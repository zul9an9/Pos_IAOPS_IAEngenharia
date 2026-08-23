// Controle negativo: devolve o manifesto PERMISSIVO (allow-all) como se o
// modelo tivesse só ecoado a entrada. Os asserts de segurança devem REPROVAR.
const BAD = `apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: sentinel-allow
  namespace: sentinel-prod
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - {}
  egress:
    - {}`;
class Bad { constructor(o){this.providerId=(o&&o.id)||'bad';} id(){return this.providerId;}
  async callApi(){ return { output: BAD, cost: 0, tokenUsage:{total:0,prompt:0,completion:0} }; } }
module.exports = Bad;
