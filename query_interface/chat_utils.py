import json
from typing import Any, List, Dict
from openai import OpenAI
from secrets import OPENAI_API_KEY
import requests
from secrets import DATABASE_INTERFACE_BEARER_TOKEN
import logging
import collections.abc
import xml.etree.ElementTree as ET

client = OpenAI(
    api_key=OPENAI_API_KEY
)


def query_database(query_prompt: str) -> Dict[str, Any]:
    """
    Query vector database to retrieve chunk with user's input questions.
    """
    url = "http://0.0.0.0:8000/query"
    headers = {
        "Content-Type": "application/json",
        "accept": "application/json",
        "Authorization": f"Bearer {DATABASE_INTERFACE_BEARER_TOKEN}",
    }
    data = {"queries": [{"query": query_prompt, "top_k": 5}]}

    response = requests.post(url, json=data, headers=headers)

    if response.status_code == 200:
        result = response.json()
        # process the result
        return result
    else:
        raise ValueError(f"Error: {response.status_code} : {response.content}")


def apply_prompt_template(question: str, wfs: str) -> str:
    """
        A helper function that applies additional template on user's question.
        Prompt engineering could be done here to improve the result. Here I will just use a minimal example.
    """
    prompt = f"""
        You are an advanced AI assistant, specializing in Property planning under building law, urban land-use plan, planning law, development plan
        etc. Your task is to use retrieved information to give consultation considering the information {wfs} and answer the customer's questions: {question}
    """
    return prompt


def call_chatgpt_api(user_question: str, chunks: List[str], wfs: str) -> Dict[str, Any]:
    """
    Call chatgpt api with user's question and retrieved chunks.
    """
    # Send a request to the GPT-3 API
    messages = list(
        map(lambda chunk: {
            "role": "user",
            "content": chunk
        }, chunks))
    question = apply_prompt_template(user_question, wfs)
    messages.append({"role": "user", "content": question})
    response = client.chat.completions.create(model="gpt-3.5-turbo-1106",
                                              messages=messages,
                                              max_tokens=1024,
                                              temperature=0.7)
    return response


def extract_with_chatgpt_api(user_question: str) -> str:
    """
    Call chatgpt api with user's question and extract numbers for "Flur" and "Flurstück"
    """
    # Send a request to the GPT-3 API
    # messages = list(map(lambda chunk: {"role": "user","content": chunk}, chunks))
    question = f"""
        Extract the numbers for "Flur" and "Flurstück" from the following text, just give me the numbers as string, and return in json format using keys "flur", "flurstueck":
         {user_question}
    """
    messages = [{"role": "user", "content": question}]
    response = client.chat.completions.create(model="gpt-3.5-turbo-0125",
                                              messages=messages,
                                              max_tokens=1024,
                                              temperature=0.7)
    json_response = response.choices[0].message.content
    print(json_response)

    return str(json_response)


def search_info_with_wfs(js: str) -> str:
    """
        Connect with WFS services to search relevant information about the specific "Flurstück"
    """
    json_flur = json.loads(js)
    #print('flur:')
    #print(json_flur['flur'])
    #print(type(json_flur['flur']))
    #print('flurstueck:')
    #print(json_flur['flurstueck'])
    #print(type(json_flur['flurstueck']))

    filter_flurstueck_part1 = ('<ogc:Filter xmlns:ogc="http://www.opengis.net/ogc" xmlns:ave="http://repository.gdi-de.org/'
                    'schemas/adv/produkt/alkis-vereinfacht/2.0"><ogc:And><ogc:PropertyIsEqualTo><ogc:PropertyName>'
                    'ave:gemarkung</ogc:PropertyName><ogc:Literal>Brandenburg</ogc:Literal></ogc:PropertyIsEqualTo>')
    if len(json_flur['flur']) == 1:
        flur = '00' + str(json_flur['flur'])
    elif len(json_flur['flur']) == 2:
        flur = '0' + str(json_flur["flur"])
    else:
        flur = str(json_flur['flur'])
    filter_flurstueck_part2 = '<ogc:PropertyIsEqualTo><ogc:PropertyName>ave:flur</ogc:PropertyName><ogc:Literal>' + flur + '</ogc:Literal></ogc:PropertyIsEqualTo>'
    # if isinstance(json_flur['flurstueck'], collections.abc.Sequence)

    if '/' in json_flur['flurstueck']:
        flstnr = json_flur['flurstueck'].split('/')
        filter_flurstueck_part3 = '<ogc:PropertyIsEqualTo><ogc:PropertyName>ave:flstnrzae</ogc:PropertyName><ogc:Literal>' + flstnr[0] + '</ogc:Literal></ogc:PropertyIsEqualTo><ogc:PropertyIsEqualTo><ogc:PropertyName>ave:flstnrnen</ogc:PropertyName><ogc:Literal>' + flstnr[1] + '</ogc:Literal></ogc:PropertyIsEqualTo>'
    else:
        filter_flurstueck_part3 = '<ogc:PropertyIsEqualTo><ogc:PropertyName>ave:flstnrzae</ogc:PropertyName><ogc:Literal>' + json_flur['flurstueck'] + '</ogc:Literal></ogc:PropertyIsEqualTo>'
    filter_flurstueck_part4 = '</ogc:And></ogc:Filter>'
    filter_flurstueck = filter_flurstueck_part1 + filter_flurstueck_part2 + filter_flurstueck_part3 + filter_flurstueck_part4
    url_flurstueck = ('https://isk.geobasis-bb.de/ows/alkis_vereinf_wfs?SERVICE=WFS&REQUEST=GetFeature&VERSION=1.1.0&'
           'TYPENAME=ave:Flurstueck&SRSNAME=urn:ogc:def:crs:EPSG::25833&FILTER=') + filter_flurstueck
    #print(url)
    response_flurstueck = requests.get(url_flurstueck)
    # print(response.text)
    root_flurstueck = ET.fromstring(response_flurstueck.text)
    ns_flurstueck = {'ave': 'http://repository.gdi-de.org/schemas/adv/produkt/alkis-vereinfacht/2.0',
          'gml': 'http://www.opengis.net/gml'}
    polygon_flurstueck = root_flurstueck.findall('.//gml:Polygon', ns_flurstueck)
    polygon_flurstueck_list = ET.tostringlist(polygon_flurstueck[0], encoding='unicode')
    polygon_flurstueck_str = ''.join(polygon_flurstueck_list)
    #el = root[1][0]
    #print(polygon_flurstueck_str)

    filter_info_part1 = ('<ogc:Filter xmlns:ogc="http://www.opengis.net/ogc" xmlns:ms="http://mapserver.gis.umn.edu/'
                            'mapserver" xmlns:gml="http://www.opengis.net/gml"><ogc:Intersects><ogc:PropertyName>'
                            'the_geom</ogc:PropertyName>')
    filter_info_part2 = polygon_flurstueck_str
    filter_info_part3 = '</ogc:Intersects></ogc:Filter>'
    filter_info = filter_info_part1 + filter_info_part2 + filter_info_part3
    url_bauplan = ('https://gdi.stadt-brandenburg.de/ws/bauleitplanung?TYPENAME=ms:Bauluecken_Flaechen&SERVICE=WFS&'
                   'version=1.1.0&REQUEST=GetFeature&srsName=urn:ogc:def:crs:EPSG::25833&FILTER=') + filter_info
    #print('url_bauplan:')
    #print(url_bauplan)

    response_bauplan = requests.get(url_bauplan)
    root_bauplan = ET.fromstring(response_bauplan.text)
    ns_bauplan = {'ms': 'http://mapserver.gis.umn.edu/mapserver',
                     'gml': 'http://www.opengis.net/gml'}
    feature_bauplan = root_bauplan.find('gml:featureMember', ns_bauplan)
    #print('feature_bauplan:')
    #print(feature_bauplan)
    if feature_bauplan is None:
        wfs_res1 = f"""
        Beim Flurstück {json_flur['flurstueck']} (Flur {json_flur['flur']}, Gemarkung Brandenburg) liegt kein Bebauungsplan vor.
    """
    else:
        wfs_res1 = f"""
        Das Flurstück {json_flur['flurstueck']} (Flur {json_flur['flur']}, Gemarkung Brandenburg) befindet sich im 
        Geltungsbereich eines Bebauungsplans. 
    """

    url_naturschutz = ('https://inspire.brandenburg.de/services/schutzg_wfs?SERVICE=WFS&REQUEST=GetFeature&VERSION='
                       '1.1.0&TYPENAME=app:nsg&SRSNAME=urn:ogc:def:crs:EPSG::25833&FILTER=') + filter_info
    #print('url_naturschutz:')
    #print(url_naturschutz)
    response_naturschutz = requests.get(url_naturschutz)
    root_naturschutz = ET.fromstring(response_naturschutz.text)
    ns_naturschutz = {'gml': 'http://www.opengis.net/gml'}
    feature_naturschutz = root_naturschutz.find('gml:featureMember', ns_naturschutz)
    #print('feature_naturschutz:')
    #print(feature_naturschutz)
    if feature_naturschutz is None:
        wfs_res2 = wfs_res1
    else:
        wfs_res2 = f"""
        Das Flurstück {json_flur['flurstueck']} (Flur {json_flur['flur']}, Gemarkung Brandenburg) befindet sich im 
        Naturschutzgebiet. 
    """
    #print('wfs_res2:')
    #print(wfs_res2)

    return wfs_res2


def ask(user_question: str) -> Dict[str, Any]:
    """
    Handle user's questions.
    """
    # extract info for "Flur" and "Flurstück"
    json_response = extract_with_chatgpt_api(user_question)
    search_result = search_info_with_wfs(json_response)
    # Get chunks from database.
    chunks_response = query_database(user_question)
    chunks = []
    for result in chunks_response["results"]:
        for inner_result in result["results"]:
            chunks.append(inner_result["text"])

    logging.info("User's questions: %s", user_question)
    logging.info("Retrieved chunks: %s", chunks)

    response = call_chatgpt_api(user_question, chunks, search_result)
    logging.info("Response: %s", response)

    return response.choices[0].message.content

def ask_with_flur(user_input: Dict[str, str]) -> Dict[str, Any]:
    """
    Handle user's questions with information about 'Flur' and 'Flurstück'.
    """
    # extract info for "Flur" and "Flurstück"
    #json_response = extract_with_chatgpt_api(user_question)
    if(user_input.flur != '0'):
        print(user_input.flur)
        json_response = '{ "flur": "' + user_input.flur + '", "flurstueck": "' + user_input.flstnrzae + '" }'
        search_result = search_info_with_wfs(json_response)
    else:
        search_result = 'Es liegen keine Informationen über Flurstück vor'
        print('search result' + search_result)
    # Get chunks from database.
    chunks_response = query_database(user_input.question)
    chunks = []
    for result in chunks_response["results"]:
        for inner_result in result["results"]:
            chunks.append(inner_result["text"])

    logging.info("User's questions: %s", user_input.question)
    logging.info("Retrieved chunks: %s", chunks)

    response = call_chatgpt_api(user_input.question, chunks, search_result)
    logging.info("Response: %s", response)

    return response.choices[0].message.content