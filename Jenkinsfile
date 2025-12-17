pipeline {
  agent any

  stages {

    stage('Build Docker Image') {
      steps {
        sh '''
          docker build -t ks-backend:latest .
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

          python --version
          pip install --upgrade pip
          pip install -r requirements.txt

          echo "=== start api locally for CI test ==="
          gunicorn -b 0.0.0.0:5000 app:app &

          sleep 3

          export API_BASE_URL=http://127.0.0.1:5000

          echo "=== run pytest ==="
          pytest tests/
        '''
      }
    }

    stage('Deploy to Kubernetes') {
      steps {
        sh '''
          export KUBECONFIG=/root/.kube/config

          echo "=== current context ==="
          kubectl config current-context

          echo "=== deploy to kubernetes ==="
          kubectl apply -f k8s
        '''
      }
    }

    stage('Smoke Test (K8s Service)') {
      steps {
        sh '''
          set -e

          echo "=== smoke test via k8s service ==="
          kubectl port-forward svc/ks-backend-svc 18080:80 &
          sleep 5

          curl -f "http://127.0.0.1:18080/api/restaurants?district=鼓山區"
        '''
      }
    }

  }
}
