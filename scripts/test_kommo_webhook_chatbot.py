from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import json
import logging

app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kommo")


@app.get("/")
async def root():
    return {
        "status": "online",
        "message": "Servidor funcionando"
    }


@app.post("/webhook/kommo")
async def kommo_webhook(request: Request):

    logger.info("=" * 60)
    logger.info("WEBHOOK DA KOMMO RECEBIDO")
    logger.info("=" * 60)

    # Corpo bruto
    body = await request.body()

    logger.info("BODY:")
    logger.info(
        body.decode("utf-8", errors="replace")
    )

    # Tenta interpretar JSON
    try:
        data = json.loads(body)

        logger.info("JSON:")
        logger.info(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False
            )
        )

    except Exception as e:
        logger.warning(
            "Não foi possível interpretar como JSON: %s",
            e
        )
        data = {}

    # ---------------------------------------------------------
    # TESTE
    # ---------------------------------------------------------

    resposta = {
        "status": "success",
        "message": "TESTE OK - Python recebeu o widget_request",
        "received": data
    }

    logger.info("Respondendo para a Kommo:")
    logger.info(
        json.dumps(
            resposta,
            indent=2,
            ensure_ascii=False
        )
    )

    return JSONResponse(
        status_code=200,
        content=resposta
    )