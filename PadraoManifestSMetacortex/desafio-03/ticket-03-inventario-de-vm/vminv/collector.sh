# Coletor de inventário de um host — SOMENTE LEITURA.
#
# Script POSIX sh, entregue por stdin a `ssh ... sh -s` em uma única sessão.
# Não usa recursos exclusivos de bash. Só mede e reporta valores crus; quem
# interpreta (compara com o baseline) é a ferramenta local, nunca este script.
#
# Saída: um único objeto JSON em stdout. Todo fato é um envelope:
#   {"read": true,  "value": <valor cru>}            fato lido (o valor pode ser vazio/zero/false)
#   {"read": false, "reason": "<motivo>"}            fato NÃO lido (sentinela distinta de "vazio")
#
# Nenhum comando abaixo cria, altera ou apaga arquivo, pacote, serviço ou
# configuração. O único redirecionamento de saída é para /dev/null.

LC_ALL=C
export LC_ALL
set -f

# Escapa um valor para uso dentro de uma string JSON (remove caracteres de controle).
esc() {
    printf '%s' "$1" | tr -d '\000-\037\177' | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'
}

str() { printf '"%s"' "$(esc "$1")"; }
ok() { printf '{"read":true,"value":%s}' "$1"; }
nao_lido() { printf '{"read":false,"reason":"%s"}' "$(esc "$1")"; }
tem() { command -v "$1" >/dev/null 2>&1; }

fato_hostname() {
    if v=$(hostname 2>/dev/null) && [ -n "$v" ]; then
        ok "$(str "$v")"
    elif v=$(uname -n 2>/dev/null) && [ -n "$v" ]; then
        ok "$(str "$v")"
    else
        nao_lido "não foi possível obter o hostname"
    fi
}

fato_coletado_em() {
    if v=$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null) && [ -n "$v" ]; then
        ok "$(str "$v")"
    else
        nao_lido "não foi possível obter a data/hora do host"
    fi
}

fato_so() {
    if [ ! -r /etc/os-release ]; then
        nao_lido "/etc/os-release ausente ou ilegível"
        return
    fi
    distribuicao=$(. /etc/os-release && printf '%s' "$ID" | tr 'A-Z' 'a-z')
    versao=$(. /etc/os-release && printf '%s' "$VERSION_ID")
    if [ -z "$distribuicao" ] || [ -z "$versao" ]; then
        nao_lido "/etc/os-release sem ID ou VERSION_ID"
        return
    fi
    ok "{\"distribuicao\":$(str "$distribuicao"),\"versao\":$(str "$versao")}"
}

fato_kernel() {
    if v=$(uname -r 2>/dev/null) && [ -n "$v" ]; then
        ok "$(str "$v")"
    else
        nao_lido "uname -r falhou"
    fi
}

fato_servicos() {
    if ! tem systemctl; then
        nao_lido "systemctl não encontrado (host sem systemd)"
        return
    fi
    if ! saida=$(systemctl list-units --type=service,socket --state=active --no-legend --plain --no-pager 2>/dev/null); then
        nao_lido "systemctl list-units falhou (systemd não está em execução?)"
        return
    fi
    lista=$(printf '%s\n' "$saida" | {
        sep=""
        while read -r unidade _carga ativo _resto; do
            case $unidade in
                *.service) tipo=service ;;
                *.socket) tipo=socket ;;
                *) continue ;;
            esac
            printf '%s{"nome":%s,"tipo":"%s","estado":%s}' "$sep" "$(str "$unidade")" "$tipo" "$(str "$ativo")"
            sep=","
        done
    })
    ok "[$lista]"
}

fato_swap() {
    if [ ! -r /proc/swaps ]; then
        nao_lido "/proc/swaps ausente ou ilegível"
        return
    fi
    if ! resumo=$(awk 'NR > 1 && NF >= 3 { n++; s += $3 } END { printf "%d %d", n + 0, s + 0 }' /proc/swaps 2>/dev/null); then
        nao_lido "não foi possível ler /proc/swaps"
        return
    fi
    set -- $resumo
    if [ "$1" -gt 0 ]; then
        ok "{\"habilitado\":true,\"tamanho_kib\":$2}"
    else
        ok '{"habilitado":false,"tamanho_kib":0}'
    fi
}

fato_portas() {
    if ! tem ss; then
        nao_lido "ss não encontrado"
        return
    fi
    if ! saida=$(ss -ltnp 2>/dev/null); then
        nao_lido "ss -ltnp falhou"
        return
    fi
    lista=$(printf '%s\n' "$saida" | {
        sep=""
        while read -r estado _rq _sq escuta _peer proc; do
            [ "$estado" = "LISTEN" ] || continue
            porta=${escuta##*:}
            endereco=${escuta%:*}
            endereco=${endereco#\[}
            endereco=${endereco%\]}
            case $porta in
                '' | *[!0-9]*) continue ;;
            esac
            case $proc in
                *'(("'*)
                    dono=${proc#*'(("'}
                    dono=${dono%%'"'*}
                    dono_json=$(ok "$(str "$dono")")
                    ;;
                *)
                    dono_json=$(nao_lido "processo dono não visível sem privilégio")
                    ;;
            esac
            printf '%s{"endereco":%s,"porta":%s,"processo":%s}' "$sep" "$(str "$endereco")" "$porta" "$dono_json"
            sep=","
        done
    })
    ok "[$lista]"
}

fato_chaves_ssh() {
    usuario=$(id -un 2>/dev/null)
    arquivo="${HOME:-}/.ssh/authorized_keys"
    if [ -z "${HOME:-}" ] || [ ! -r "$arquivo" ]; then
        nao_lido "authorized_keys do usuário que conectou ausente ou ilegível"
        return
    fi
    # Só metadados de identificação; o material da chave (blob) nunca é emitido.
    lista=$(grep -v -e '^[[:space:]]*#' -e '^[[:space:]]*$' "$arquivo" | {
        sep=""
        while IFS= read -r linha; do
            tipo=""
            comentario=""
            estado=0
            for palavra in $linha; do
                case $estado in
                    0)
                        case $palavra in
                            ssh-* | ecdsa-* | sk-*)
                                tipo=$palavra
                                estado=1
                                ;;
                        esac
                        ;;
                    1) estado=2 ;;
                    2) comentario=${comentario:+$comentario }$palavra ;;
                esac
            done
            [ -n "$tipo" ] || continue
            if tem ssh-keygen && fp=$(printf '%s\n' "$linha" | ssh-keygen -lf - 2>/dev/null) && [ -n "$fp" ]; then
                fp=$(printf '%s\n' "$fp" | awk '{ print $2 }')
                fp_json=$(ok "$(str "$fp")")
            else
                fp_json=$(nao_lido "ssh-keygen indisponível ou não conseguiu ler a chave")
            fi
            printf '%s{"tipo":%s,"comentario":%s,"fingerprint":%s}' "$sep" "$(str "$tipo")" "$(str "$comentario")" "$fp_json"
            sep=","
        done
    })
    ok "{\"escopo\":\"usuario_conectado\",\"usuario\":$(str "$usuario"),\"arquivo\":\".ssh/authorized_keys\",\"chaves\":[$lista]}"
}

fato_ssh_login_root() {
    sshd_bin=$(command -v sshd 2>/dev/null)
    if [ -z "$sshd_bin" ]; then
        for candidato in /usr/sbin/sshd /sbin/sshd /usr/local/sbin/sshd; do
            if [ -x "$candidato" ]; then
                sshd_bin=$candidato
                break
            fi
        done
    fi
    if [ -z "$sshd_bin" ]; then
        nao_lido "binário sshd não encontrado"
        return
    fi
    if ! saida=$("$sshd_bin" -T 2>/dev/null); then
        nao_lido "sshd -T falhou (privilégio insuficiente para ler a configuração efetiva)"
        return
    fi
    valor=$(printf '%s\n' "$saida" | awk 'tolower($1) == "permitrootlogin" { print tolower($2); exit }')
    if [ -z "$valor" ]; then
        nao_lido "sshd -T não reportou permitrootlogin"
        return
    fi
    ok "$(str "$valor")"
}

fato_ntp() {
    if ! tem systemctl || [ ! -d /run/systemd/system ]; then
        nao_lido "systemd não está em execução; mecanismo de tempo não verificável"
        return
    fi
    ativo=""
    for unidade in systemd-timesyncd chrony chronyd ntp ntpd ntpsec; do
        if systemctl is-active --quiet "$unidade" 2>/dev/null; then
            ativo=$unidade
            break
        fi
    done
    if [ -n "$ativo" ]; then
        ok "{\"mecanismo\":$(str "$ativo"),\"ativo\":true}"
    else
        ok '{"mecanismo":"nenhum","ativo":false}'
    fi
}

main() {
    coletado_em=$(fato_coletado_em)
    hostname_json=$(fato_hostname)
    so=$(fato_so)
    kernel=$(fato_kernel)
    servicos=$(fato_servicos)
    swap=$(fato_swap)
    portas=$(fato_portas)
    chaves=$(fato_chaves_ssh)
    login_root=$(fato_ssh_login_root)
    ntp=$(fato_ntp)
    printf '{"formato":1,"coletado_em":%s,"hostname":%s,"so":%s,"kernel":%s,"servicos":%s,"swap":%s,"portas":%s,"chaves_ssh":%s,"ssh_login_root":%s,"ntp":%s}\n' \
        "$coletado_em" "$hostname_json" "$so" "$kernel" "$servicos" "$swap" "$portas" "$chaves" "$login_root" "$ntp"
}

# stdin do script é o próprio script (sh -s): impede que qualquer comando o consuma.
main </dev/null
exit 0
