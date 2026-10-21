
pipeline {
    agent any

    stages {
        stage('Verificar repositorio') {
            steps {
                sh 'ls -la'
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
