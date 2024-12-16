# 1. Vérifier les configurations VNC dans le conteneur ib-gateway
kubectl exec -n ib-gateway $(kubectl get pod -n ib-gateway -l app=ibgateway -o name) -- bash -c '
echo "=== VNC Process Check ==="
ps aux | grep vnc
echo
echo "=== VNC Port Listening ==="
netstat -tunlp | grep 5900
echo
echo "=== IP Configuration ==="
ip addr show
echo
echo "=== Environment Variables ==="
env | grep -i vnc
'

# 2. Vérifier les logs détaillés
kubectl logs -n ib-gateway $(kubectl get pod -n ib-gateway -l app=ibgateway -o name) --all-containers

# 3. Vérifier la communication entre noVNC et ib-gateway
kubectl exec -n ib-gateway $(kubectl get pod -n ib-gateway -l app.kubernetes.io/component=novnc -o name) -- bash -c '
echo "=== Testing connection to ib-gateway ==="
nc -zv ibgateway 5900
echo
echo "=== DNS Resolution ==="
nslookup ibgateway
echo
echo "=== Network Route ==="
traceroute ibgateway
'

# 4. Vérifier les services et endpoints
kubectl get svc,ep -n ib-gateway