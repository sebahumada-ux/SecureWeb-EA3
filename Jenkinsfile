
pipeline {
    agent any

    options {
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    parameters {
        booleanParam(
            name: 'EJECUTAR_SONARQUBE',
            defaultValue: false,
            description: 'Analizar codigo con SonarQube'
        )

        booleanParam(
            name: 'EJECUTAR_DEPENDENCY_CHECK',
            defaultValue: false,
            description: 'Analizar dependencias con OWASP Dependency-Check'
        )

        booleanParam(
            name: 'EJECUTAR_ZAP',
            defaultValue: false,
            description: 'Ejecutar analisis pasivo con OWASP ZAP'
        )

        booleanParam(
            name: 'EJECUTAR_DEPLOY',
            defaultValue: false,
            description: 'Preparar paquete de despliegue de la version segura'
        )
    }

    stages {

        stage('Verificar repositorio') {
            steps {
                echo 'Verificando archivos de SecureWeb-EA3'

                sh '''
                    set -e
                    ls -la
                    test -f app.py
                    test -f app_secure.py
                    test -f requirements.txt
                    test -f Dockerfile
                    test -f tests/test_app_secure.py
                '''
            }
        }

        stage('Build') {
            steps {
                echo 'Preparando entorno Python'

                sh '''
                    set -e

                    mkdir -p "$WORKSPACE@tmp"

                    python3 -m venv "$WORKSPACE@tmp/secureweb-venv"

                    "$WORKSPACE@tmp/secureweb-venv/bin/python" \
                        -m pip install \
                        --no-cache-dir \
                        --disable-pip-version-check \
                        -r requirements.txt pytest

                    echo "Build completado"
                '''
            }
        }

        stage('Test') {
            steps {
                echo 'Ejecutando pruebas automatizadas con pytest'

                sh '''
                    set -e

                    "$WORKSPACE@tmp/secureweb-venv/bin/python" \
                        -m pytest -q tests \
                        --junitxml=pytest-results.xml
                '''
            }
        }

        stage('Analyze - SonarQube') {
            when {
                expression {
                    params.EJECUTAR_SONARQUBE
                }
            }

            steps {
                echo 'Ejecutando analisis de SonarQube'

                script {
                    def scannerHome = tool 'SonarQube-Scanner'

                    withSonarQubeEnv('SonarQube-EA3') {
                        sh "${scannerHome}/bin/sonar-scanner"
                    }
                }
            }
        }

        stage('Dependency-Check') {
            when {
                expression {
                    params.EJECUTAR_DEPENDENCY_CHECK
                }
            }

            steps {
                echo 'Analizando dependencias con OWASP Dependency-Check'

                timeout(time: 25, unit: 'MINUTES') {
                    dependencyCheck(
                        odcInstallation: 'Dependency-Check',
                        nvdCredentialsId: 'nvd-api-key-ea3',
                        additionalArguments: '''
                            --scan .
                            --format ALL
                            --out .
                            --enableExperimental
                            --disableRetireJs
                            --nvdApiDelay 8000
                            --nvdMaxRetryCount 3
                        '''.trim().replaceAll('\\s+', ' '),
                        stopBuild: true
                    )
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
                        "$WORKSPACE@tmp/secureweb-venv/bin/python" \
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

                            "$WORKSPACE@tmp/secureweb-venv/bin/python" - <<'PY'
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
            when {
                expression {
                    params.EJECUTAR_DEPLOY
                }
            }

            steps {
                echo 'Preparando entrega de la aplicacion segura'

                sh '''
                    set -e

                    mkdir -p release

                    cp app_secure.py release/app.py
                    cp requirements.txt release/
                    cp Dockerfile release/

                    git rev-parse --short HEAD \
                        > release/VERSION

                    "$WORKSPACE@tmp/secureweb-venv/bin/python" - <<'PY'
import importlib.util

spec = importlib.util.spec_from_file_location(
    "secure_release_app",
    "release/app.py"
)

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

client = module.app.test_client()
response = client.get("/hello?name=TEST")

assert response.status_code == 200
assert b"Hello, TEST!" in response.data

print("Smoke test del paquete: OK")
PY

                    tar -czf \
                        secureweb-ea3-release.tar.gz \
                        -C release .

                    echo "Paquete de despliegue preparado"
                '''
            }
        }
    }

    post {
        always {
            script {
                if (
                    params.EJECUTAR_DEPENDENCY_CHECK &&
                    fileExists('dependency-check-report.xml')
                ) {
                    dependencyCheckPublisher(
                        pattern: '**/dependency-check-report.xml',
                        skipNoReportFiles: true
                    )
                }
            }

            archiveArtifacts(
                artifacts: 'pytest-results.xml,dependency-check-report.*,zap-report.*,flask-zap.log,secureweb-ea3-release.tar.gz',
                allowEmptyArchive: true
            )
        }

        success {
            echo 'Pipeline finalizado correctamente'
        }

        failure {
            echo 'Pipeline con errores. Revisar Console Output.'
        }
    }
}
