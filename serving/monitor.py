import httpx
import pandas as pd
import re
import time
import urllib3
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from dotenv import load_dotenv
load_dotenv()

def extrair_concursos():
    url = "https://www.in.gov.br/consulta/-/buscar/dou"
    termos = [
        "ciencia de dados", "inteligencia artificial", "machine learning",
        "aprendizado de maquina", "sql", "cientista de dados",
        "inteligencia da informacao", "analise de dados", "analista de dados",
        "data science", "data analyst", "Aprendizagem de Máquina", "data analytics"
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0', 'X-Requested-With': 'XMLHttpRequest'}
    resultados = []

    with httpx.Client(timeout=40.0, verify=False) as client:
        for termo in termos:
            params = {
                'q': f'"{termo}"', 's': 'todos', 'exactDate': 'semana',
                'sortType': '0', 'delta': '100', 'artType': 'Edital de Concurso Público'
            }
            try:
                resp = client.get(url, params=params, headers=headers)
                texto = resp.text
                titulos = re.findall(r'"title":"(.*?)"', texto)
                urls = re.findall(r'"urlTitle":"(.*?)"', texto)
                datas = re.findall(r'"pubDate":"(.*?)"', texto)

                for i in range(len(titulos)):
                    resultados.append({
                        'Data': datas[i],
                        'Termo': termo,
                        'Titulo': titulos[i].encode().decode('unicode_escape').replace('\\', ''),
                        'Link': f"https://www.in.gov.br/web/dou/-/{urls[i]}"
                    })
                time.sleep(1)
            except: continue

    if not resultados:
        return None

    df = pd.DataFrame(resultados)
    df = df.groupby(['Link', 'Data', 'Titulo'])['Termo'].apply(lambda x: ', '.join(set(x))).reset_index()
    return df
def enviar_email(df):
    email_origem = os.environ.get('EMAIL_USER')
    senha_origem = os.environ.get('EMAIL_PASS')
    email_destino = os.environ.get('EMAIL_DESTINY')

    msg = MIMEMultipart()
    msg['From'] = email_origem
    msg['To'] = email_destino
    msg['Subject'] = f"🚀 Radar DOU: {len(df)} Oportunidades de Dados"

    # Criamos a tabela em HTML para o corpo do email
    # O 'render_links=True' faz com que os links fiquem clicáveis!
    tabela_html = df.to_html(index=False, render_links=True, classes='table table-striped')

    # Estilo CSS básico para a tabela não ficar feia no email
    html_corpo = f"""
    <html>
      <head>
        <style>
          table {{ border-collapse: collapse; width: 100%; font-family: sans-serif; }}
          th {{ background-color: #f2f2f2; text-align: left; padding: 8px; border-bottom: 2px solid #ddd; }}
          td {{ padding: 8px; border-bottom: 1px solid #ddd; font-size: 12px; }}
          tr:nth-child(even) {{ background-color: #f9f9f9; }}
          a {{ color: #1a73e8; text-decoration: none; font-weight: bold; }}
        </style>
      </head>
      <body>
        <h2>Radar de Concursos da Semana</h2>
        <p>Olá! Encontramos <b>{len(df)}</b> editais que batem com suas palavras-chave:</p>
        {tabela_html}
        <br>
        <p><i>Este é um monitoramento automático via GitHub Actions.</i></p>
      </body>
    </html>
    """
    
    msg.attach(MIMEText(html_corpo, 'html'))

    # Mantemos o anexo CSV por segurança
    filename = "radar_concursos.csv"
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    with open(filename, "rb") as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= {filename}")
        msg.attach(part)

    # Envio via SMTP
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(email_origem, senha_origem)
    server.send_message(msg)
    server.quit()

# Execução principal
dados = extrair_concursos()
if dados is not None:
    enviar_email(dados)
    print("E-mail enviado com sucesso!")
else:
    print("Nenhum edital encontrado esta semana.")