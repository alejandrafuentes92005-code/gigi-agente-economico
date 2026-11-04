#######################
# Agente Basico De IA #
# Herramientas        #
#######################

import os
import requests

class IntermediateTools:

    def __init__(self):
        pass

    # Herramienta para consultar el tipo de cambio 
    def consultar_tipo_cambio_api(self, moneda: str):
       

        if not moneda:
            return "Error: Se requiere el código de la moneda para obtener el tipo de cambio."

        # URL del servicio para obtener el tipo de cambio según la moneda:
        url = f"https://open.er-api.com/v6/latest/{moneda.upper()}"

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()  # Lanza una excepción si la respuesta no es exitosa
            return response.json()  # Intentar decodificar la respuesta como JSON
        except Exception as e:
            print(f"Error al obtener_tipo_cambio_api: {moneda}. Error: {e}")
            return f"ERROR: No se pudo obtener el tipo de cambio para la moneda: {moneda}"
        
        # Herramienta para consultar el precio de una criptomoneda (CoinGecko)
    def consultar_precio_criptomoneda(self, criptomoneda: str, moneda: str):
       

        if not criptomoneda:
            return "Error: Se requiere el nombre de la criptomoneda."

        if not moneda:
            return "Error: Se requiere la moneda en la que se desea consultar el precio."

        # URL de CoinGecko para obtener el precio de una criptomoneda
        url = "https://api.coingecko.com/api/v3/simple/price"

        parametros = {
            "ids": criptomoneda.lower(),
            "vs_currencies": moneda.lower()
        }

        try:
            response = requests.get(url, params=parametros, timeout=30)
            response.raise_for_status()
            return response.json()

        except Exception as e:
            print(
                f"Error al consultar_precio_criptomoneda: "
                f"{criptomoneda}. Error: {e}"
            )
            return (
                f"ERROR: No se pudo obtener el precio de la criptomoneda: "
                f"{criptomoneda}"
            )
        
        # Herramienta para consultar datos económicos del Banco Mundial
    def obtener_datos_economicos_world_bank(
        self, pais: str, indicador: str
    ):

        if not pais:
            return "Error: Se requiere el código del país."

        if not indicador:
            return "Error: Se requiere el código del indicador económico."

        # URL de la API del Banco Mundial
        url = (
            f"https://api.worldbank.org/v2/country/"
            f"{pais.upper()}/indicator/{indicador}"
        )

        parametros = {
            "format": "json",
            "per_page": 10
        }

        try:
            response = requests.get(
                url,
                params=parametros,
                timeout=30
            )

            response.raise_for_status()

            datos = response.json()

            return datos

        except Exception as e:
            print(
                f"Error al obtener_datos_economicos_world_bank: "
                f"{pais}, {indicador}. Error: {e}"
            )
            return (
                f"ERROR: No se pudieron obtener los datos económicos "
                f"para {pais}"
            )

                # Herramienta para consultar información de países (countries.dev)
    def consultar_informacion_pais_countries_dev(self, pais: str):
    

        if not pais:
            return "Error: Se requiere el código del país."

        # URL de countries.dev
        url = f"https://countries.dev/alpha/{pais.upper()}"

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            return response.json()

        except Exception as e:
            print(
                f"Error al consultar_informacion_pais_countries_dev: "
                f"{pais}. Error: {e}"
            )
            return (
                f"ERROR: No se pudo obtener la información del país: {pais}"
            )

        
            # Herramienta para consultar la deuda pública de EE. UU. (U.S. Treasury)
    def consultar_deuda_eeuu_treasury(self, fecha: str = None):

        url = (
            "https://api.fiscaldata.treasury.gov/services/api/"
            "fiscal_service/v2/accounting/od/debt_to_penny"
        )

        parametros = {
            "format": "json",
            "sort": "-record_date",
            "page[size]": 1
        }

        # Si el usuario proporciona una fecha, se consulta esa fecha
        if fecha:
            parametros["filter"] = f"record_date:eq:{fecha}"

        try:
            response = requests.get(url, params=parametros, timeout=30)
            response.raise_for_status()

            return response.json()

        except Exception as e:
            print(f"Error al consultar_deuda_eeuu_treasury: {e}")
            return "ERROR: No se pudo obtener la deuda pública de EE. UU."


    # Herramienta para consultar datos de comercio internacional
    def consultar_comercio_internacional_uncomtrade(
        self,
        anio: int = 2023,
        flujo: str = "exportaciones"
    ):
        flujo = flujo.lower().strip()

        if flujo in ["exportaciones", "exportacion", "export"]:
            flow_code = "X"
        elif flujo in ["importaciones", "importacion", "import"]:
            flow_code = "M"
        else:
            return "Error: Usa 'exportaciones' o 'importaciones'."

        url = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"

        params = {
            "reporterCode": 320,
            "period": str(anio),
            "flowCode": flow_code,
            "partnerCode": 0,
            "cmdCode": "TOTAL"
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            datos = response.json()
            registros = datos.get("data", [])

            if not registros:
                return f"No se encontraron datos para Guatemala en {anio}."

            resultado = []

            for registro in registros[:10]:
                resultado.append({
                    "pais": registro.get("reporterDesc"),
                    "anio": registro.get("period"),
                    "flujo": registro.get("flowDesc"),
                    "socio_comercial": registro.get("partnerDesc"),
                    "producto": registro.get("cmdDesc"),
                    "valor_comercio_usd": registro.get("primaryValue")
                })

            return {
                "fuente": "UN Comtrade",
                "pais_consultado": "Guatemala",
                "anio": anio,
                "tipo_comercio": flujo,
                "registros": resultado
            }

        except requests.exceptions.RequestException as e:
            print(f"Error al consultar UN Comtrade: {e}")
            return "ERROR: No se pudieron obtener los datos de comercio."

        except (ValueError, TypeError) as e:
            print(f"Error al procesar los datos de UN Comtrade: {e}")
            return "ERROR: La respuesta de UN Comtrade no fue válida."
