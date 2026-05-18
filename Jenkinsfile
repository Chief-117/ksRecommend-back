pipeline {
  agent any

  options {
    disableConcurrentBuilds()
    timeout(time: 30, unit: 'MINUTES')
  }

  environment {
    BACKEND_IMAGE    = "noahhh117/ks-backend:latest"
    JMETER_IMAGE_REPO = "noahhh117/ks-jmeter"
    JMETER_IMAGE_TAG  = "latest"
  }

  stages {

    stage('Build & Push Backend Image') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'dockerhub', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
          sh '''
            set -e
            echo "=== 🐳 開始打包後端 Docker 映像檔 ==="
            docker build -t ${BACKEND_IMAGE} .

            echo "=== 🔑 登入 Docker Hub 並推行映像檔 ==="
            echo "${DOCKER_PASS}" | docker login -u "${DOCKER_USER}" --password-stdin
            docker push ${BACKEND_IMAGE}
            echo "=== 🟢 後端 Image 成功推送到 Docker Hub ==="
          '''
        }
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
          pip install --upgrade pip
          pip install -r requirements.txt

          echo "=== start api locally for CI test ==="
          gunicorn -b 0.0.0.0:5000 app:app &
          APP_PID=$!

          # 確保無論成功或失敗都會 kill gunicorn
          trap "echo '=== stop local api ===' && kill $APP_PID 2>/dev/null || true" EXIT

          sleep 3
          export API_BASE_URL=http://127.0.0.1:5000
          pytest tests/
        '''
      }
    }

    stage('Deploy to Kubernetes') {
      steps {
        sh '''
          set -e
          echo "=== 🔍 自動搜尋 kube-ci/config 絕對路徑 ==="
          export KUBECONFIG=$(find "$(pwd)" -type f -path "*kube-ci/config" | head -n 1)
          if [ -z "$KUBECONFIG" ]; then
            echo "❌ 錯誤：找不到 kube-ci/config！"
            exit 1
          fi
          echo "=== 使用 KUBECONFIG: $KUBECONFIG ==="

          echo "=== 🚀 部署最新設定到 Kubernetes ==="
          kubectl apply -f k8s --validate=false

          echo "=== 🔄 強制觸抓最新 Docker Hub 映像檔並重啟 Pod ==="
          kubectl rollout restart deployment/ks-backend
        '''
      }
    }

    stage('Smoke Test (K8s Service)') {
      steps {
        sh '''
          set -e
          export KUBECONFIG=$(find "$(pwd)" -type f -path "*kube-ci/config" | head -n 1)

          echo "=== ⏳ 等待後端 Pod 滾動更新完成 ==="
          kubectl rollout status deployment/ks-backend --timeout=120s

          # 用 BUILD_NUMBER 避免 Pod 名稱衝突
          CURL_POD="curl-test-${BUILD_NUMBER}"

          echo "=== 🔍 測試 K8s 內部 Service 通訊 ==="
          if kubectl run ${CURL_POD}-80 --image=curlimages/curl:8.5.0 --rm -i --restart=Never --timeout=15s -- \
              curl -f "http://ks-backend-svc/api/restaurants?district=%E9%BC%93%E5%B1%B1%E5%8D%80"; then
            echo "=== 🟢 透過 Service 預設 Port (80) 連線成功 ==="
          elif kubectl run ${CURL_POD}-8000 --image=curlimages/curl:8.5.0 --rm -i --restart=Never --timeout=15s -- \
              curl -f "http://ks-backend-svc:8000/api/restaurants?district=%E9%BC%93%E5%B1%B1%E5%8D%80"; then
            echo "=== 🟢 透過 Service 指定 Port (8000) 連線成功 ==="
          elif kubectl run ${CURL_POD}-5000 --image=curlimages/curl:8.5.0 --rm -i --restart=Never --timeout=15s -- \
              curl -f "http://ks-backend-svc:5000/api/restaurants?district=%E9%BC%93%E5%B1%B1%E5%8D%80"; then
            echo "=== 🟢 透過 Service 指定 Port (5000) 連線成功 ==="
          else
            echo "❌ 錯誤：無法透過 Service 連線到後端！"
            exit 1
          fi
        '''
      }
    }

    stage('Build & Push JMeter Image') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'dockerhub', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
          sh '''
            set -e
            FULL_JMETER_IMAGE="${JMETER_IMAGE_REPO}:${JMETER_IMAGE_TAG}"

            echo "=== 🐳 打包 JMeter Docker 映像檔 ==="
            docker build -f Dockerfile.jmeter -t ks-jmeter:latest .
            docker tag ks-jmeter:latest "${FULL_JMETER_IMAGE}"

            echo "=== 🔑 登入 Docker Hub 並推行 JMeter 映像檔 ==="
            echo "${DOCKER_PASS}" | docker login -u "${DOCKER_USER}" --password-stdin
            docker push "${FULL_JMETER_IMAGE}"
            echo "=== 🟢 JMeter Image 成功推送到 Docker Hub ==="
          '''
        }
      }
    }

    stage('API Load Test (JMeter)') {
      steps {
        sh '''
          set -e
          export KUBECONFIG=$(find "$(pwd)" -type f -path "*kube-ci/config" | head -n 1)
          FULL_JMETER_IMAGE="${JMETER_IMAGE_REPO}:${JMETER_IMAGE_TAG}"

          echo "=== 🧹 強制清空 K8s 殘留的壓測 Pod ==="
          kubectl delete pod jmeter-test --grace-period=0 --force --ignore-not-found=true

          kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: jmeter-test
spec:
  restartPolicy: Never
  containers:
    - name: jmeter
      image: \${FULL_JMETER_IMAGE}
      imagePullPolicy: Always
      command: ["sh","-c"]
      args:
        - |
          echo "=== jmeter start ==="
          rm -rf /results && mkdir -p /results/html
          jmeter -n \\
            -t /jmeter/restaurants_api.jmx \\
            -l /results/result.jtl \\
            -e -o /results/html
          echo "=== jmeter done ==="
          sleep 300
EOF

          kubectl wait --for=condition=Ready pod/jmeter-test --timeout=240s

          echo "=== ⏳ 等待 JMeter 執行完成（最多 5 分鐘）==="
          FOUND_DONE=0
          for i in $(seq 1 60); do
            # 若 Pod 已進入 Failed 狀態，提早跳出
            POD_PHASE=$(kubectl get pod jmeter-test -o jsonpath='{.status.phase}' 2>/dev/null || echo "Unknown")
            if [ "$POD_PHASE" = "Failed" ]; then
              echo "❌ JMeter Pod 執行失敗（Pod phase: Failed）"
              kubectl logs jmeter-test || true
              exit 1
            fi

            if kubectl logs jmeter-test 2>/dev/null | grep -q "=== jmeter done ==="; then
              FOUND_DONE=1
              break
            fi
            sleep 5
          done

          if [ "$FOUND_DONE" != "1" ]; then
            echo "❌ JMeter 執行超時，未在預期時間內完成"
            kubectl logs jmeter-test || true
            exit 1
          fi

          echo "=== 📥 複製報告到 Jenkins workspace ==="
          mkdir -p jmeter/report
          kubectl cp jmeter-test:/results/result.jtl jmeter/report/result.jtl
          kubectl cp jmeter-test:/results/html jmeter/report/html

          echo "=== 🧹 清除壓測 Pod ==="
          kubectl delete pod jmeter-test --ignore-not-found=true
        '''
      }
    }

  }

  post {
    always {
      archiveArtifacts artifacts: 'jmeter/report/**', fingerprint: true, allowEmptyArchive: true
    }
    success {
      echo '✅ Pipeline 全部完成！'
    }
    failure {
      echo '❌ Pipeline 執行失敗，請檢查上方 log。'
    }
  }
}