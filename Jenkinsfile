pipeline {
  agent any

  options {
    disableConcurrentBuilds()
  }

  environment {
    // 👇 已修改為你在 Docker Hub 的後端映像檔完整名稱
    BACKEND_IMAGE = "noahhh117/ks-backend:latest"

    JMETER_IMAGE_REPO = "noahhh117/ks-jmeter"
    JMETER_IMAGE_TAG  = "latest"
  }

  stages {

    stage('Build & Push Backend Image') {
      steps {
        // 使用你在 Jenkins 裡設定好的 dockerhub 憑證登入並推行
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
          sleep 3

          export API_BASE_URL=http://127.0.0.1:5000
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

          echo "=== 🔍 測試 K8s 內部 Service 通訊 ==="
          # 💡 依據 app.py 與 service.yaml 設定，全面測試連接埠通訊
          if kubectl run curl-test --image=curlimages/curl:8.5.0 --rm -i --restart=Never --timeout=15s -- curl -f "http://ks-backend-svc/api/restaurants?district=%E9%BC%93%E5%B1%B1%E5%8D%80"; then
            echo "=== 🟢 透過 Service 預設 Port (80) 連線成功 ==="
          elif kubectl run curl-test-8000 --image=curlimages/curl:8.5.0 --rm -i --restart=Never --timeout=15s -- curl -f "http://ks-backend-svc:8000/api/restaurants?district=%E9%BC%93%E5%B1%B1%E5%8D%80"; then
            echo "=== 🟢 透過 Service 指定 Port (8000) 連線成功 ==="
          elif kubectl run curl-test-5000 --image=curlimages/curl:8.5.0 --rm -i --restart=Never --timeout=15s -- curl -f "http://ks-backend-svc:5000/api/restaurants?district=%E9%BC%93%E5%B1%B1%E5%8D%80"; then
            echo "=== 🟢 透過 Service 指定 Port (5000) 連線成功 ==="
          else
            echo "❌ 錯誤：無法透過 Service 連線到後端！"
            exit 1
          fi
        '''
      }
    }

    stage('Build JMeter Docker Image') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'dockerhub', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
          sh '''
            set -e
            docker build -f Dockerfile.jmeter -t ks-jmeter:latest .
            FULL_JMETER_IMAGE="${JMETER_IMAGE_REPO}:${JMETER_IMAGE_TAG}"
            docker tag ks-jmeter:latest "${FULL_JMETER_IMAGE}"
            echo "${DOCKER_PASS}" | docker login -u "${DOCKER_USER}" --password-stdin
            docker push "${FULL_JMETER_IMAGE}"
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

          # 💡 這裡就是修改的地方：在建立新 Pod 前，使用大絕招強制把舊的壓測 Pod 徹底拔除，不留任何快取殘留！
          echo "=== 🧹 強制清空 K8s 殘留的壓測 Pod 並等待釋放 ==="
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

          FOUND_DONE=0
          for i in \$(seq 1 60); do
            if kubectl logs jmeter-test 2>/dev/null | grep -q "=== jmeter done ==="; then
              FOUND_DONE=1
              break
            fi
            sleep 5
          done

          if [ "\$FOUND_DONE" != "1" ]; then exit 1; fi

          mkdir -p jmeter/report
          kubectl cp jmeter-test:/results/result.jtl jmeter/report/result.jtl
          kubectl cp jmeter-test:/results/html jmeter/report/html
          kubectl delete pod jmeter-test --ignore-not-found=true
        '''
      }
    }

  }

  post {
    always {
      archiveArtifacts artifacts: 'jmeter/report/**', fingerprint: true, allowEmptyArchive: true
    }
  }
}