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
                    }
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
                artifacts: 'pytest-results.xml,dependencias-arbol.txt,dependencias-bloqueadas.txt,dependencias-desactualizadas.txt,auditoria-dependencias.json,flask-deploy.log,respuesta-deploy.txt',
                allowEmptyArchive: true
            )
        }

        unstable {
            echo 'ALERTA: pipeline inestable. Revisar informe de vulnerabilidades y registros de Jenkins.'
        }

        failure {
            echo 'ALERTA: fallo el pipeline. Revisar Console Output para corregir el problema.'
        }

        success {
            echo 'Pipeline EA 3.3.2 finalizado correctamente.'
        }
    }
}
