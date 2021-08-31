import re
import base64
import time
from pytrustnfe.nfse.ginfes import xml_recepcionar_lote_rps
from pytrustnfe.nfse.ginfes import recepcionar_lote_rps
from pytrustnfe.nfse.ginfes import consultar_situacao_lote
from pytrustnfe.nfse.ginfes import consultar_lote_rps
from pytrustnfe.nfse.ginfes import cancelar_nfse

from pytrustnfe.certificado import Certificado
from odoo.exceptions import UserError


def _convert_values(rps):
    result = {"lista_rps": rps}

    for vals in rps:
        # Numero lote
        result["numero_lote"] = vals["numero_rps"]
        result["inscricao_municipal"] = re.sub(
            "[^0-9]", "", vals["emissor"]["inscricao_municipal"]
        )
        result["cnpj_prestador"] = re.sub("[^0-9]", "", vals["emissor"]["cnpj"])

        # IdentificacaoRps ~ Status
        vals["numero"] = vals["numero_rps"]
        vals["tipo_rps"] = "1"
        vals["natureza_operacao"] = "1"

        if vals["regime_tributario"] == "simples":
            vals["regime_tributacao"] = "2"
            vals["optante_simples"] = "1"
        else:
            vals["regime_tributacao"] = "2"
            vals["optante_simples"] = "2"

        vals["incentivador_cultural"] = "2"
        vals["status"] = "1"

        # Rps Substituído - não está sendo usado no momento

        # Valores
        vals["valor_deducao"] = "0"
        if vals["valor_iss"] > 0:
            vals["iss_retido"] = "1"
            vals["valor_iss_retido"] = vals["iss_valor_retencao"]
        else:
            vals["iss_retido"] = "2"
            vals["valor_iss_retido"] = 0

        vals["aliquota_issqn"] = "%.4f" % abs(vals["itens_servico"][0]["aliquota"])

        # ValorServicos - ValorPIS - ValorCOFINS - ValorINSS - ValorIR - ValorCSLL - OutrasRetençoes
        # - ValorISSRetido - DescontoIncondicionado - DescontoCondicionado)
        vals["valor_liquido_nfse"] = (
            vals["valor_servico"]
            - (vals.get("valor_pis") or 0)
            - (vals.get("valor_cofins") or 0)
            - (vals.get("valor_inss") or 0)
            - (vals.get("valor_ir") or 0)
            - (vals.get("valor_csll") or 0)
            - (vals.get("outras_retencoes") or 0)
            - (vals.get("valor_iss_retido") or 0)
        )

        # Código Serviço
        cod_servico = vals["itens_servico"][0]["codigo_servico"]
        for item_servico in vals["itens_servico"]:
            if item_servico["codigo_servico"] != cod_servico:
                raise UserError(
                    "Não é possível gerar notas de serviço com linhas que possuem código de serviço diferentes."
                    + "\nPor favor, verifique se todas as linhas de serviço possuem o mesmo código de serviço."
                    + "\nNome: %s: Código de serviço: %s\nNome: %s: Código de serviço: %s"
                    % (
                        vals["itens_servico"][0]["name"],
                        cod_servico,
                        item_servico["name"],
                        item_servico["codigo_servico"],
                    )
                )
        vals["codigo_servico"] = cod_servico
        vals["codigo_tributacao_municipio"] = vals["itens_servico"][0][
            "codigo_servico_municipio"
        ]

        # Descricao - Código Municipio
        vals["descricao"] = vals["discriminacao"]
        vals["codigo_municipio"] = vals["emissor"]["codigo_municipio"]

        # Tomador
        vals["tomador"]["tipo_cpfcnpj"] = 2 if vals["tomador"]["empresa"] else 1
        vals["tomador"].update(vals["tomador"]["endereco"])
        vals["tomador"]["cidade"] = vals["tomador"]["codigo_municipio"]

        # Prestador
        vals["prestador"] = {}
        vals["prestador"]["cnpj"] = re.sub("[^0-9]", "", vals["emissor"]["cnpj"])
        vals["prestador"]["inscricao_municipal"] = re.sub(
            "[^0-9]", "", vals["emissor"]["inscricao_municipal"]
        )
        vals["prestador"]["cidade"] = vals["emissor"]["codigo_municipio"]

        # Itens Servico
        itens_servico = []
        for item in vals["itens_servico"]:
            itens_servico.append(
                {
                    "descricao": item.name,
                    "quantidade": str("%.2f" % item.quantidade),
                    "valor_unitario": str("%.2f" % item.valor_unitario),
                }
            )

            vals["prestador"]["cnae"] = re.sub(
                "[^0-9]", "", item.codigo_servico_municipio or ""
            )

        vals["itens_servico"] = itens_servico

        # Intermediario e ConstrucaoCivil - não está sendo usado no momento

    return result


def send_api(certificate, password, edocs):
    cert_pfx = base64.decodestring(certificate)
    certificado = Certificado(cert_pfx, password)

    nfse_values = _convert_values(edocs)
    xml_enviar = xml_recepcionar_lote_rps(certificado, nfse=nfse_values)

    recebe_lote = recepcionar_lote_rps(
        certificado, xml=xml_enviar, ambiente=edocs[0]["ambiente"]
    )

    retorno = recebe_lote["object"]
    if "NumeroLote" in dir(retorno):
        recibo_nfe = retorno.Protocolo
        time.sleep(5)

        consulta = {
            "cnpj_prestador": re.sub("[^0-9]", "", edocs[0]["emissor"]["cnpj"]),
            "inscricao_municipal": re.sub(
                "[^0-9]", "", edocs[0]["emissor"]["inscricao_municipal"]
            ),
            "protocolo": recibo_nfe,
        }

        consulta_situacao = consultar_situacao_lote(
            certificado,
            consulta=consulta,
            ambiente=edocs[0]["ambiente"],
        )

        ret_rec = consulta_situacao["object"]

        if "Situacao" in dir(ret_rec):
            if ret_rec.Situacao in (3, 4):
                consulta_lote = consultar_lote_rps(
                    certificado, consulta=consulta, ambiente=edocs[0]["ambiente"]
                )
                retLote = consulta_lote["object"]

                if "ListaNfse" in dir(retLote):
                    return {
                        "code": 201,
                        "entity": {
                            "protocolo_nfe": retLote.ListaNfse.CompNfse.Nfse.InfNfse.CodigoVerificacao,
                            "numero_nfe": retLote.ListaNfse.CompNfse.Nfse.InfNfse.Numero,
                        },
                        "xml": retLote["sent_xml"].encode("utf-8"),
                    }
                else:
                    mensagem_retorno = retLote.ListaMensagemRetorno.MensagemRetorno

                    return {
                        "code": 400,
                        "api_code": mensagem_retorno.Codigo,
                        "message": mensagem_retorno.Mensagem,
                    }
            elif ret_rec.Situacao == 1:
                return {
                    "code": 400,
                    "api_code": "1",
                    "message": "Aguardando envio",
                }
            else:
                return {
                    "code": 400,
                    "api_code": "2",
                    "message": "Lote aguardando processamento",
                }
        else:
            mensagem_retorno = ret_rec.ListaMensagemRetorno.MensagemRetorno

            return {
                "code": 400,
                "api_code": mensagem_retorno.Codigo,
                "message": mensagem_retorno.Mensagem,
            }
    else:
        mensagem_retorno = retorno.ListaMensagemRetorno.MensagemRetorno

        return {
            "code": 400,
            "api_code": mensagem_retorno.Codigo,
            "message": mensagem_retorno.Mensagem,
        }


def cancel_api(certificate, password, vals):
    cert_pfx = base64.decodestring(certificate)
    certificado = Certificado(cert_pfx, password)
    canc = {
        "cnpj_prestador": vals["cnpj_cpf"],
        "inscricao_municipal": vals["inscricao_municipal"],
        "cidade": vals["codigo_municipio"],
        "numero_nfse": vals["numero"],
        "codigo_cancelamento": "1",
        "senha": vals["user_password"],
    }

    cancel = cancelar_nfse(certificado, cancelamento=canc, ambiente=vals["ambiente"])

    retorno = cancel["object"].Body.CancelarNfseResponse.CancelarNfseResult
    if "Cancelamento" in dir(retorno):
        return {
            "code": 200,
            "message": "Nota Fiscal Cancelada",
        }
    else:
        # E79 - Nota já está cancelada
        if retorno.ListaMensagemRetorno.MensagemRetorno.Codigo != "E79":
            mensagem = "%s - %s" % (
                retorno.ListaMensagemRetorno.MensagemRetorno.Codigo,
                retorno.ListaMensagemRetorno.MensagemRetorno.Mensagem,
            )
            raise UserError(mensagem)

        return {
            "code": 200,
            "message": "Nota Fiscal Cancelada",
        }
