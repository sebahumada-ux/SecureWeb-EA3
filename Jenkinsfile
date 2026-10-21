
pipeline {
    agent any

    stages {
        stage('Verificar repositorio') {
            steps {
                sh 'ls -la'
            }
        }

        stage('Build') {
            steps {
                sh '''
                    set -e
                    python3 -m venv "$WORKSPACE@tmp/secureweb-venv"
                    "$WORKSPACE@tmp/secureweb-venv/bin/python" -m pip install --disable-pip-version-check -r requirements.txt pytest
                '''
            }
        }

        stage('Test') {
            steps {
                sh '''
                    "$WORKSPACE@tmp/secureweb-venv/bin/python" -m pytest -q tests
                '''
            }
        }

        stage('Analyze - SonarQube') {
            steps {
                script {
                    def scannerHome = tool 'SonarQube-Scanner'

                    withSonarQubeEnv('SonarQube-EA3') {
                        sh "${scannerHome}/bin/sonar-scanner"
                    }
                }
            }
        }

        stage('Dependency-Check') {
            steps {
                dependencyCheck(
                    odcInstallation: 'Dependency-Check',
                    nvdCredentialsId: 'nvd-api-key-ea3',
                    additionalArguments: '--scan . --format ALL --out . --enableExperimental'
                )
            }
        }
    }

    post {
        always {
            dependencyCheckPublisher(
                pattern: '**/dependency-check-report.xml',
                skipNoReportFiles: true
            )
        }
    }
}
