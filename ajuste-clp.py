#//////////////////////////////////////////////////////////////////////////////
#Autor:Luigi Capoia
#Data:05/2023
#Esse script foi criado para ajustar a data e hora dos CLP
#comments for dummies
#//////////////////////////////////////////////////////////////////////////////
#Import
import requests
import mysql.connector
import json
import time
from datetime import datetime
from suds.client import Client
import zeep
#//////////////////////////////////////////////////////////////////////////////
# DATA
#//////////////////////////////////////////////////////////////////////////////

#Função para fatiar uma lista
def chunks(lista, n):
    for i in range(0, len(lista), n):
        yield lista[i:i + n]



#Função para criar um codigo verificador do clp 
def crc16(data : bytearray, offset , length):
    if data is None or offset < 0 or offset > len(data)- 1 and offset+length > len(data):
        return 0
    crc = 0xFFFF
    for i in range(0, length):
        crc ^= data[offset + i] << 8
        for j in range(0,8):
            if (crc & 0x8000) > 0:
                crc =(crc << 1) ^ 0x1021
            else:
                crc = crc << 1
    return crc & 0xFFFF

#Informa a data atual
data_atual = datetime.today()

#formatação da data
#dia
dia_em_texto = "{}".format(data_atual.day)
#mes
mes_em_texto = "{}".format(data_atual.month)
#ano
ano_em_texto = data_atual.strftime("%y")
#dia da semana
numero_do_dia_da_semana = data_atual.strftime("%w")
#hora
hora_em_texto = "{}".format(data_atual.hour)
#minutos
min_em_texto = "{}".format(data_atual.minute)
#segundos
seg_em_texto = "{}".format(data_atual.second)

print(data_atual)

#Fazer a junção e transforma em Hexa  (adicionando uma mascara 02X no numero hexa)
dataHexx =(f'{int(dia_em_texto):02X}')+(f'{int(mes_em_texto):02X}')+(f'{int(ano_em_texto):02X}')+(f'{int(numero_do_dia_da_semana):02X}')+(f'{int(hora_em_texto):02X}')+(f'{int(min_em_texto):02X}')+(f'{int(seg_em_texto):02X}') +'FF'
print(dataHexx)

#Adiciona o prefixo (5801) + comando de escrita (02) + configuração da data e hora (11)
dataHex = bytes.fromhex('58010211'+ dataHexx)
crc=(crc16(dataHex,0,len(dataHex)))  #Calcula o codigo verificador do numero
print(crc)

dataHexCrc ='58010211'+dataHexx+(f'{crc:02X}')   #Adiciona o codigo verificador ao numero
print((dataHexCrc))

# Adiciona o SIN e MIN para o servidor da Orbcomm
dataHexCrcOrbcomm = '7B81' + dataHexCrc #7b  = 123  e 81 =129

#Transforma o comando de Hexa para decimal e coloca em uma lista
data_decimal= [int(dataHexCrcOrbcomm[i:i+2], 16) for i in range(0, len(dataHexCrcOrbcomm), 2)]
print(data_decimal)

#transforma em binario para o servidor da Onix
dataHexCrcOnix = bytes.fromhex(dataHexCrc)

#//////////////////////////////////////////////////////////////////////////////
#BANCO
#//////////////////////////////////////////////////////////////////////////////

#conecta com banco de Dados
mydb  = mysql.connector.connect(
 host    =     "000.000.000.000",
 port=3000,
 user="admin",
 password="admin",
 database="database"
)

# cria os array da Orbcomm e da Onix
serialsOrbcomm = []
serialsONix = []

# Faz a consulta na tabela do banco de dados
mycursor = mydb.cursor()
mycursor.execute("SELECT ")
myresult = mycursor.fetchall()

# Monta uma lista das estações conforme é solicitado "no caso foi solicitado (C) e (S)"
for estacao in myresult:

    if estacao[3] != None and 'C' in estacao[2] :
        serialsOrbcomm.append(estacao[3])

    if estacao[3] != None and 'S' in estacao[2] :
        serialsONix.append(estacao[3])



# Adiciona aos arrays as estações de 100 em 100 mas pode ser alterado esse valor
ArryOrbcomm = list(chunks(serialsOrbcomm, 100))
ArryOnix = list(chunks(serialsONix, 100))



#Orbcomm
# Envia a hora para o servidor da Orbcomm utilizando as credenciais e a url, a data deve ser em decimal.
# A hora é repassada para os transmissores que devolvem uma mensssagem.
# Metodo utilizado foi o Json e requests.
for enviaOrbcon in ArryOrbcomm :
    url = ""
    credencialOrbcomm = {
    "access_id": "00000", #Login 
    "password": "000000", #Senha 
    "destinations": ','.join(enviaOrbcon), #Transmissores
    "message": {  #Menssagem a ser enviada
    "DestinationID": "",
    "UserMessageID": 0,
    "RawPayload": data_decimal  #Data em decimal 
    }
    }
    print(credencialOrbcomm)
    headers = {'Content-type': 'application/json', 'charset': 'utf-8'}  #Cabeçalho da mensagem 
    result = requests.post(url, data=json.dumps(credencialOrbcomm), headers=headers) #Fução que envia a mensagem
    print(result.content)
    time.sleep(20) #Função para mandar a mensagem a cada segundo (no caso vai ser 20s)




#ONIX
# Envia a hora para o servidor da Onix utilizando as credenciais e a url, a data deve ser em decimal.
# A hora e repassada para os transmissores que devolvem uma mensssagem.
# Metodo utilizado foi o Zeep e Soap.
for enviaOnix in ArryOnix : #Cria um for para enviar a todos os transmissores
    comandoArr = []        #Cria um novo Array
    for isn in enviaOnix:  #Cria um for para emviar a menssagem abaixo
        comandoArr.append({  #Junta os transmissores
            'isn': isn,
            'tipo': 1,
            'dados': dataHexCrcOnix  #Data deve sem em binario na Onix
        })
  
    wsdl_url = '' #Aqui começa as credenciais da Onix
    client = zeep.Client(wsdl=wsdl_url)
    credenciais = {
        'login': '00000',  # Login
        'senha': '00000',  # Senha 
        'comandos': {
            'Comando': comandoArr  #Transmissores
        }
    }
    SendMenssages = client.service.EnviarComandos(**credenciais) #Comando que envia as mensagens 
    # print(SendMenssages)
    # print(credenciais)
    time.sleep(20) #Função para mandar a mensagem a cada segundo (no caso vai ser 20s)

# /////////////////////////////////////////////////////////////////////////////

