pipeline {
  agent any

  options {
    disableConcurrentBuilds()
  }

  environment {
    IMAGE_NAME = "ks-backend:latest"
    // 移除全域 KUBECONFIG 設定，改由各 Stage 內動態自動搜尋，避免路徑對不上的問題

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
          
          echo "=== 🔍 自動搜尋 kube-ci/config 絕對路徑 ==="
          export KUBECONFIG=$(find "$(pwd)" -type f -path "*kube-ci/config" | head -n 1)
          
          if [ -z "$KUBECONFIG" ]; then
            echo "❌ 錯誤：在專案中找不到 kube-ci/config 檔案！目前目錄結構如下："
            find . -maxdepth 3
            exit 1
          fi
          echo "成功載入 KUBECONFIG的路徑為: ${KUBECONFIG}"

          echo "=== kubeconfig context ==="
          kubectl config current-context

          echo "=== 🚚 導出 Docker 映像檔並強制打包給 Minikube ==="
          docker save ${IMAGE_NAME} -o backend.tar

          kubectl run image-loader --image=docker:24.0.7 --restart=Never --overrides='
          {
            "spec": {
              "hostPID": true,
              "containers": [
                {
                  "name": "loader",
                  "image": "docker:24.0.7",
                  "command": ["sleep", "3600"],
                  "volumeMounts": [
                    {"name": "docker-sock", "mountPath": "/var/run/docker.sock"}
                  ]
                }
              ],
              "volumes": [
                {"name": "docker-sock", "hostPath": {"path": "/var/run/docker.sock"}}
              ]
            }
          }'
          
          echo "⏳ 等待傳輸容器啟動..."
          kubectl wait --for=condition=Ready pod/image-loader --timeout=30s
          
          echo "📤 傳送映像檔檔案中..."
          kubectl cp backend.tar image-loader:/backend.tar
          
          echo "📥 在 Minikube 內部解壓載入映像檔..."
          kubectl exec image-loader -- docker load -i /backend.tar
          
          echo "🧹 清理傳輸快取..."
          kubectl delete pod image-loader --ignore-not-found=true
          rm -f backend.tar

          echo "=== 🗑️ 先行強制清除舊部署，避免滾動更新卡死 ==="
          kubectl delete deployment ks-backend --ignore-not-found=true

          echo "=== deploy to kubernetes ==="
          kubectl apply -f k8s --validate=false
        '''
      }
    }

    stage('Smoke Test (K8s Service)') {
      steps {
        sh '''
          set -e

          echo "=== 🔍 自動搜尋 kube-ci/config 絕對路徑 ==="
          export KUBECONFIG=$(find "$(pwd)" -type f -path "*kube-ci/config" | head -n 1)

          echo "=== ⏳ 等待後端 Pod 確實啟動完成 ==="
          kubectl rollout status deployment/ks-backend --timeout=120s

          echo "=== smoke test via k8s service ==="
          # 為了防止 Service 外部開 80 但內部轉 5000 導致對不上，我們直接自動判定嘗試
          if kubectl run curl-test --image=curlimages/curl:8.5.0 --rm -i --restart=Never --timeout=15s -- curl -f "http://ks-backend-svc/api/restaurants?district=%E9%BC%93%E5%B1%B1%E5%8D%80"; then
            echo "=== 🟢 透過預設 Port (80) 連線成功 ==="
          elif kubectl run curl-test-5000 --image=curlimages/curl:8.5.0 --rm -i --restart=Never --timeout=15s -- curl -f "http://ks-backend-svc:5000/api/restaurants?district=%E9%BC%93%E5%B1%B1%E5%8D%80"; then
            echo "=== 🟢 透過指定 Port (5000) 連線成功 ==="
          else
            echo "❌ 錯誤：無法透過 Service 連線到後端，請確認 k8s/service.yaml 的 port 設定！"
            exit 1
          fi

          echo "=== smoke test passed ==="
        '''
      }
    }

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

          echo "=== 🔍 自動搜尋 kube-ci/config 絕對路徑 ==="
          export KUBECONFIG=$(find "$(pwd)" -type f -path "*kube-ci/config" | head -n 1)

          echo "=== run jmeter load test ==="
          FULL_JMETER_IMAGE="${JMETER_IMAGE_REPO}:${JMETER_IMAGE_TAG}"

          # 清掉殘留
          kubectl delete pod jmeter-test --ignore-not-found=true

          # 建立 Pod
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

          # 等 Pod Ready
          kubectl wait --for=condition=Ready pod/jmeter-test --timeout=240s || {
            kubectl describe pod jmeter-test || true
            exit 1
          }

          echo "=== wait jmeter done log ==="
          FOUND_DONE=0
          for i in \$(seq 1 60); do
            if kubectl logs jmeter-test 2>/dev/null | grep -q "=== jmeter done ==="; then
              FOUND_DONE=1
              break
            fi
            echo "[wait] not done yet... (\${i}/60)"
            sleep 5
          done

          if [ "\$FOUND_DONE" != "1" ]; then
            echo "ERROR: jmeter did not finish in time"
            exit 1
          fi

          echo "=== copy jmeter result ==="
          mkdir -p jmeter/report
          kubectl cp jmeter-test:/results/result.jtl jmeter/report/result.jtl
          kubectl cp jmeter-test:/results/html jmeter/report/html

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