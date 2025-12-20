pipeline {
  agent any

  options {
    disableConcurrentBuilds()
  }

  environment {
    IMAGE_NAME = "ks-backend:latest"
    KUBECONFIG = "/root/.kube/config-ci"

    // 你提供的 Docker Hub repo（這個是對的）
    JMETER_IMAGE_REPO = "t55619/ks-jmeter"
    JMETER_IMAGE_TAG  = "latest"
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

    /* ========= 新增：只負責 build JMeter image，不影響你原本流程 ========= */
    stage('Build JMeter Docker Image') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'dockerhub', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
          sh '''
            set -e
            echo "=== build jmeter docker image ==="
            docker build -f Dockerfile.jmeter -t ks-jmeter:latest .

            echo "=== tag & push jmeter image ==="
            FULL_JMETER_IMAGE="${JMETER_IMAGE_REPO}:${JMETER_IMAGE_TAG}"

            docker tag ks-jmeter:latest "${FULL_JMETER_IMAGE}"

            echo "${DOCKER_PASS}" | docker login -u "${DOCKER_USER}" --password-stdin

            docker push "${FULL_JMETER_IMAGE}"

            echo "=== pushed: ${FULL_JMETER_IMAGE} ==="
          '''
        }
      }
    }

    stage('API Load Test (JMeter)') {
      steps {
        sh '''
          set -e

          echo "=== run jmeter load test ==="

          echo "=== where am i ==="
          pwd
          echo "=== list workspace root ==="
          ls -al

          FULL_JMETER_IMAGE="${JMETER_IMAGE_REPO}:${JMETER_IMAGE_TAG}"
          echo "=== using image: ${FULL_JMETER_IMAGE} ==="

          # 清掉殘留（避免 AlreadyExists）
          kubectl delete pod jmeter-test --ignore-not-found=true

          # 用你 push 上去的 ks-jmeter image（B 的核心）
          kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: jmeter-test
spec:
  restartPolicy: Never
  containers:
    - name: jmeter
      image: ${FULL_JMETER_IMAGE}
      imagePullPolicy: Always
      command: ["sh","-c"]
      args:
        - |
          echo "=== jmeter start ==="
          rm -rf /results && mkdir -p /results/html

          # Dockerfile.jmeter 已 COPY jmeter/ -> /jmeter
          jmeter -n \
            -t /jmeter/restaurants_api.jmx \
            -l /results/result.jtl \
            -e -o /results/html

          echo "=== jmeter done ==="
          # 留時間給 Jenkins kubectl cp
          sleep 300
EOF

          # 等 Pod Ready（含 image pull）
          kubectl wait --for=condition=Ready pod/jmeter-test --timeout=240s || {
            echo "=== jmeter pod describe ==="
            kubectl describe pod jmeter-test || true
            echo "=== jmeter pod events ==="
            kubectl get events --sort-by=.lastTimestamp | tail -n 50 || true
            exit 1
          }

          echo "=== wait jmeter done log ==="
          FOUND_DONE=0
          for i in $(seq 1 60); do
            if kubectl logs jmeter-test 2>/dev/null | grep -q "=== jmeter done ==="; then
              FOUND_DONE=1
              break
            fi
            echo "[wait] not done yet... (${i}/60)"
            sleep 5
          done

          if [ "$FOUND_DONE" != "1" ]; then
            echo "ERROR: jmeter did not finish in time"
            echo "=== jmeter logs ==="
            kubectl logs jmeter-test || true
            echo "=== jmeter describe ==="
            kubectl describe pod jmeter-test || true
            exit 1
          fi

          echo "=== copy jmeter result ==="
          mkdir -p jmeter/report
          kubectl cp jmeter-test:/results/result.jtl jmeter/report/result.jtl
          kubectl cp jmeter-test:/results/html jmeter/report/html

          echo "=== verify local result ==="
          ls -al jmeter/report
          test -f jmeter/report/result.jtl || {
            echo "ERROR: result.jtl not found in workspace after kubectl cp"
            exit 1
          }

          # 清理
          kubectl delete pod jmeter-test --ignore-not-found=true

          echo "=== jmeter finished ==="
        '''
      }
    }

  }

  post {
    always {
      echo "=== archive jmeter report ==="
      archiveArtifacts artifacts: 'jmeter/report/**', fingerprint: true, allowEmptyArchive: true
    }
  }
}
