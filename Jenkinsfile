pipeline {
  agent any

  environment {
    IMAGE_NAME = "ks-backend:latest"
    KUBECONFIG = "/root/.kube/config-ci"
  }

  stages {

    stage('Build Docker Image') {
      steps {
        sh '''
          set -e
          echo "=== build docker image ==="
          docker build -t ${IMAGE_NAME} .
        '''
      }
    }

    stage('Run CI API Tests (Local)') {
      agent {
        docker {
          image 'python:3.10-slim'
        }
      }
      steps {
        sh '''
          set -e

          echo "=== install deps ==="
          python --version
          pip install --upgrade pip
          pip install -r requirements.txt

          echo "=== start api locally for CI test ==="
          gunicorn -b 0.0.0.0:5000 app:app &
          APP_PID=$!

          sleep 3

          export API_BASE_URL=http://127.0.0.1:5000

          echo "=== run pytest ==="
          pytest tests/

          echo "=== stop local api ==="
          kill $APP_PID
        '''
      }
    }

    stage('Deploy to Kubernetes') {
      steps {
        sh '''
          set -e

          echo "=== kubeconfig context ==="
          kubectl config current-context

          echo "=== deploy to kubernetes ==="
          kubectl apply -f k8s --validate=false
        '''
      }
    }

    stage('Smoke Test (K8s Service)') {
      steps {
        sh '''
          set -e

          echo "=== smoke test via k8s service ==="

          kubectl run curl-test \
            --image=curlimages/curl:8.5.0 \
            --rm -i --restart=Never \
            -- \
            curl -f "http://ks-backend-svc/api/restaurants?district=鼓山區"

          echo "=== smoke test passed ==="
        '''
      }
    }

    stage('API Load Test (JMeter)') {
      agent {
        docker {
          image 'justb4/jmeter:latest'
        }
      }
      steps {
        sh '''
          set -e

          echo "=== run jmeter load test ==="

          jmeter -n \
            -t jmeter/restaurants_api.jmx \
            -l jmeter/result.jtl \
            -e -o jmeter/report
        '''
      }
      post {
        always {
          echo "=== archive jmeter results ==="
          archiveArtifacts artifacts: 'jmeter/**', fingerprint: true
        }
      }
    }

  }
}
