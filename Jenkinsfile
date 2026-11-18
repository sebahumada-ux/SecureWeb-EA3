pipeline {
    agent any

    options {
        disableConcurrentBuilds()
        timeout(time: 20, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    parameters {
        booleanParam(
            name: 'EJECUTAR_SONARQUBE',
            defaultValue: false,
            description: 'Activar SonarQube solo si su contenedor esta encendido'
        )

        booleanParam(
            name: 'EJECUTAR_ZAP',
            defaultValue: false,
            description: 'Ejecutar OWASP ZAP sobre Flask seguro y generar informes HTML/JSON'
        )

        booleanParam(
            name: 'PROBAR_NOTIFICACION_ALERTA',
            defaultValue: false,
            description: 'Simula estado UNSTABLE para probar Mailpit sin introducir vulnerabilidades'
        )
    }

    environment {
        PIPENV_BIN = '/var/jenkins_home/pipenv-ea332/bin/pipenv'
        PIPENV_NOSPIN = '1'
        PIPENV_IGNORE_VIRTUALENVS = '1'
    }

    stages {
        stage('Build') {
            steps {
                sh '''
                    set -eu
                    test -f Pipfile
                    test -f Pipfile.lock
                    test -f app_secure.py
                    test -f tests/test_app_secure.py
                    test -x "$PIPENV_BIN"

                    "$PIPENV_BIN" verify
                    "$PIPENV_BIN" sync --dev --clean
                    echo "Build: dependencias instaladas desde Pipfile.lock"
                '''
            }
        }

        stage('Test') {
            steps {
                sh '''
                    set -eu
                    "$PIPENV_BIN" run python -m pytest -q tests --junitxml=pytest-results.xml
                '''
            }
        }

        stage('Analyze') {
            steps {
                sh '''
                    set -eu
                    "$PIPENV_BIN" run python -m compileall -q app_secure.py tests
                    "$PIPENV_BIN" run python -m pip check
                    echo "Analisis basico de sintaxis y dependencias: OK"
                '''

                script {
                    if (params.EJECUTAR_SONARQUBE) {
                        def scannerHome = tool 'SonarQube-Scanner'
                        withSonarQubeEnv('SonarQube-EA3') {
                            sh(scannerHome + '/bin/sonar-scanner')
                        }
                    } else {
                        echo 'SonarQube desactivado para ahorrar recursos.'
                    }
                }
            }
        }

        stage('Dependency Management') {
            steps {
                sh '''
                    set -eu
                    "$PIPENV_BIN" verify
                    "$PIPENV_BIN" graph > dependencias-arbol.txt
                    "$PIPENV_BIN" requirements --dev > dependencias-bloqueadas.txt

                    if "$PIPENV_BIN" update --outdated > dependencias-desactualizadas.txt 2>&1; then
                        echo "Consulta de actualizaciones realizada."
                    else
                        echo "No fue posible consultar todas las actualizaciones." >> dependencias-desactualizadas.txt
                    fi

                    AUDIT_ENV="$WORKSPACE@tmp/secureweb-audit-venv"
                    if [ ! -x "$AUDIT_ENV/bin/pip-audit" ]; then
                        python3 -m venv "$AUDIT_ENV"
                        "$AUDIT_ENV/bin/python" -m pip install --disable-pip-version-check pip-audit
                    fi
                '''

                script {
                    def auditStatus = 0
                    timeout(time: 6, unit: 'MINUTES') {
                        auditStatus = sh(
                            script: '''
                                set -eu
                                "$WORKSPACE@tmp/secureweb-audit-venv/bin/pip-audit" \
                                    -r dependencias-bloqueadas.txt \
                                    --format json \
                                    --output auditoria-dependencias.json \
                                    --progress-spinner off
                            ''',
                            returnStatus: true
                        )
                    }

                    if (auditStatus == 1) {
                        unstable('ALERTA: se detectaron vulnerabilidades conocidas en dependencias. Revisar auditoria-dependencias.json')
                    } else if (auditStatus != 0) {
                        error('No se pudo completar la auditoria de dependencias')
                    } else {
                        echo 'Auditoria: sin vulnerabilidades conocidas detectadas por pip-audit.'
                        if (params.PROBAR_NOTIFICACION_ALERTA) {
                            unstable('SIMULACION DE ALERTA: estado UNSTABLE para probar la notificacion, sin vulnerabilidades reales.')
                        }
                    }
                }
            }
        }

        stage('Security Test - ZAP') {
            when {
                expression {
                    params.EJECUTAR_ZAP
                }
            }

            steps {
                echo 'Preparando Flask seguro para analisis ZAP'

                sh '''
                    set -e

                    JENKINS_NODE_COOKIE=dontKillMe nohup \
                        "$PIPENV_BIN" run python \
                        -m flask --app app_secure run \
                        --host=0.0.0.0 \
                        --port=5000 \
                        --no-reload \
                        > flask-zap.log 2>&1 < /dev/null &

                    echo $! > .flask-zap.pid

                    READY=0

                    for i in 1 2 3 4 5 6 7 8 9 10; do
                        if curl -fsS --max-time 3 \
                            'http://127.0.0.1:5000/hello?name=TEST' \
                            > /dev/null; then
                            READY=1
                            break
                        fi

                        sleep 2
                    done

                    if [ "$READY" -ne 1 ]; then
                        cat flask-zap.log
                        exit 1
                    fi

                    echo "Flask disponible para ZAP"
                '''

                withCredentials([
                    string(
                        credentialsId: 'zap-api-key-ea3',
                        variable: 'ZAP_API_KEY'
                    )
                ]) {
                    timeout(time: 5, unit: 'MINUTES') {
                        sh '''
                            set +x

                            "$PIPENV_BIN" run python - <<'PY'
import os
import json
import time
import urllib.parse
import urllib.request
from collections import Counter

zap_url = "http://zap-ea3:8090"
target = "http://jenkins-ea3:5000/hello?name=TEST"
api_key = os.environ["ZAP_API_KEY"]


def zap_request(path, **params):
    query = urllib.parse.urlencode(params)
    url = zap_url + path + "?" + query

    request = urllib.request.Request(
        url,
        headers={"X-ZAP-API-Key": api_key}
    )

    with urllib.request.urlopen(
        request, timeout=30
    ) as response:
        data = response.read()

    if "/JSON/" in path:
        result = json.loads(data)

        if isinstance(result, dict) and "code" in result:
            raise RuntimeError(str(result))

        return result

    return data


print("Conectando con OWASP ZAP...")

version = zap_request("/JSON/core/view/version/")
print("ZAP:", version.get("version"))

print("Iniciando sesion nueva de OWASP ZAP para evitar hallazgos antiguos")
zap_request("/JSON/core/action/newSession/", overwrite="true")

print("Analizando:", target)

zap_request(
    "/JSON/core/action/accessUrl/",
    url=target,
    followRedirects="true"
)

for attempt in range(30):
    status = zap_request(
        "/JSON/pscan/view/recordsToScan/"
    )

    pending = int(status["recordsToScan"])

    if pending == 0:
        break

    time.sleep(3)
else:
    raise RuntimeError(
        "ZAP no completo el analisis pasivo"
    )

report = zap_request(
    "/OTHER/core/other/htmlreport/"
)

with open("zap-report.html", "wb") as file:
    file.write(report)

results = zap_request(
    "/JSON/core/view/alerts/",
    baseurl="http://jenkins-ea3:5000",
    start="0",
    count="500"
)

alerts = results.get("alerts", [])

with open("zap-report.json", "w") as file:
    json.dump(
        {"alerts": alerts},
        file,
        indent=2
    )

risks = Counter(
    alert.get("risk", "Unknown")
    for alert in alerts
)

print("Resultados del analisis ZAP:")
print("Alto:", risks.get("High", 0))
print("Medio:", risks.get("Medium", 0))
print("Bajo:", risks.get("Low", 0))
print("Informativo:", risks.get("Informational", 0))

print("Informes generados:")
print("zap-report.html")
print("zap-report.json")

if risks.get("High", 0) > 0:
    raise RuntimeError(
        "Se detectaron alertas de riesgo alto"
    )
PY
                        '''
                    }
                }
            }

            post {
                always {
                    sh '''
                        if [ -f .flask-zap.pid ]; then
                            kill "$(cat .flask-zap.pid)" \
                                2>/dev/null || true

                            rm -f .flask-zap.pid
                        fi
                    '''
                }
            }
        }

        stage('Deploy') {
            steps {
                sh '''
                    set -eu
                    echo "Desplegando aplicacion segura en entorno temporal de prueba"

                    "$PIPENV_BIN" run python -m flask --app app_secure run \
                        --host 127.0.0.1 --port 5053 --no-reload \
                        > flask-deploy.log 2>&1 &
                    APP_PID=$!
                    trap 'kill "$APP_PID" 2>/dev/null || true' EXIT

                    READY=0
                    for i in 1 2 3 4 5 6 7 8 9 10; do
                        if curl -fsS --max-time 3 'http://127.0.0.1:5053/hello?name=TEST' \
                            > respuesta-deploy.txt; then
                            READY=1
                            break
                        fi
                        sleep 2
                    done

                    if [ "$READY" -ne 1 ]; then
                        cat flask-deploy.log
                        exit 1
                    fi

                    grep -Fq 'Hello, TEST!' respuesta-deploy.txt
                    echo "Deploy temporal y prueba HTTP: OK"
                '''
            }
        }
    }

    post {
        always {
            junit testResults: 'pytest-results.xml', allowEmptyResults: true

            archiveArtifacts(
                artifacts: 'pytest-results.xml,dependencias-arbol.txt,dependencias-bloqueadas.txt,dependencias-desactualizadas.txt,auditoria-dependencias.json,flask-deploy.log,respuesta-deploy.txt,zap-report.*,flask-zap.log',
                allowEmptyArchive: true
            )
        }

        unstable {
            echo 'ALERTA: pipeline inestable. Revisar auditoria o simulacion en los registros.'
            mail(
                to: 'prueba@example.test',
                subject: "[EV3] ALERTA UNSTABLE - ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                body: """Jenkins registro un resultado UNSTABLE.
Puede ser por vulnerabilidades conocidas o por la simulacion de aviso de prueba.
Revisa Console Output y el archivo auditoria-dependencias.json.
Trabajo: ${env.JOB_NAME}
Ejecucion: #${env.BUILD_NUMBER}
Detalle: ${env.BUILD_URL}
"""
            )
        }

        failure {
            echo 'ALERTA: fallo el pipeline. Revisar Console Output para corregir el problema.'
            mail(
                to: 'prueba@example.test',
                subject: "[EV3] ERROR FAILURE - ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                body: """El pipeline Jenkins fallo.
Trabajo: ${env.JOB_NAME}
Ejecucion: #${env.BUILD_NUMBER}
Revisa los errores en: ${env.BUILD_URL}
"""
            )
        }

        success {
            echo 'Pipeline EV3 finalizado correctamente.'
            mail(
                to: 'prueba@example.test',
                subject: "[EV3] SUCCESS - ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                body: """Pipeline completado correctamente.
Build, Test, Analyze, Dependency Management y Deploy finalizaron sin errores.
La auditoria no encontro vulnerabilidades conocidas.
Trabajo: ${env.JOB_NAME}
Ejecucion: #${env.BUILD_NUMBER}
Detalle: ${env.BUILD_URL}
"""
            )
        }
    }
}
