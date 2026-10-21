
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
    }
}
