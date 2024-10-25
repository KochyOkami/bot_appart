import json
from random import randint
import time
import requests
import mysql.connector
from mysql.connector import Error
import re
from bs4 import BeautifulSoup
from seLoger import cookies, headers
from token_bot import MYSQL_PASSWORD, MYQL_USER, DATABASE
from config import PRICE_LIMIT, ENERGY_CLASSIFICATION, DEBUG

# Connexion à la base de données MySQL


def create_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database=DATABASE,
            user=MYQL_USER,
            password=MYSQL_PASSWORD
        )
        if connection.is_connected():
            print("Connexion réussie à MySQL")
            return connection
    except Error as e:
        print(f"Erreur lors de la connexion à MySQL : {e}")
        return None


def insert_new_rent_ad(connection, id, title, description, price, safetyDeposit, agencyRentalFee, surfaceArea, roomsQuantity, energyClassification, thumbnailUrl, url):
    try:
        cursor = connection.cursor()
        sql_query = '''INSERT INTO rent_ads (id, title, description, price, safetyDeposit, agencyRentalFee, surfaceArea, roomsQuantity, energyClassification, thumbnailUrl, url) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'''
        cursor.execute(sql_query, (id, title, description, price, safetyDeposit, agencyRentalFee,
                       surfaceArea, roomsQuantity, energyClassification, thumbnailUrl, url))
        connection.commit()
        return {"id": id, "title": title, "description": description, "price": price, "safetyDeposit": safetyDeposit, "agencyRentalFee": agencyRentalFee, "surfaceArea": surfaceArea, "roomsQuantity": roomsQuantity, "energyClassification": energyClassification, "thumbnailUrl": thumbnailUrl, "url": url}

    except Error as e:
        print(f"Erreur lors de l'insertion : {e}")


def check_if_ad_already_saved(connection, id):
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM rent_ads WHERE id = %s", (id,))
    return cursor.fetchone() is not None


def mots_absents(chaine, mots):
    # Créer un motif d'expression régulière avec tous les mots à vérifier
    motif = r'\b(' + '|'.join(re.escape(mot) for mot in mots) + r')\b'
    if re.search(motif, chaine):
        return False  # Un mot interdit a été trouvé
    return True  # Aucun mot interdit n'a été trouvé


def get_bienIci_ads(connection):
    # URL de la requête avec les filtres
    url = "https://www.bienici.com/realEstateAds.json?filters=%7B%22size%22%3A24%2C%22from%22%3A0%2C%22showAllModels%22%3Afalse%2C%22filterType%22%3A%22rent%22%2C%22propertyType%22%3A%5B%22house%22%2C%22flat%22%2C%22loft%22%2C%22castle%22%2C%22townhouse%22%5D%2C%22maxPrice%22%3A550%2C%22minArea%22%3A20%2C%22energyClassification%22%3A%5B%22A%22%2C%22B%22%2C%22C%22%2C%22D%22%5D%2C%22page%22%3A1%2C%22sortBy%22%3A%22relevance%22%2C%22sortOrder%22%3A%22desc%22%2C%22onTheMarket%22%3A%5Btrue%5D%2C%22limit%22%3A%22_%60q%60H%7BiiB%3F%7Byy%40%60tQdB%3Fnsy%40%22%2C%22newProperty%22%3Afalse%2C%22blurInfoType%22%3A%5B%22disk%22%2C%22exact%22%5D%2C%22zoneIdsByTypes%22%3A%7B%22zoneIds%22%3A%5B%22-76306%22%5D%7D%7D&extensionType=extendedIfNoResult&access_token=wGfLVViuDdn6GYnacpzlAfCw%2BXjcJQiiNpxIACm9Bj0%3D%3A6717b2f399e62400b173340a"

    # Faire la requête HTTP GET
    response = requests.get(url)
    new_ads = []
    # Vérifier si la requête a réussi (code HTTP 200)
    if response.status_code == 200:
        # Extraire le JSON de la réponse
        data = response.json()

        for ad in data.get('realEstateAds', []):
            id = ad.get('id')
            title = ad.get('title')
            description = ad.get('description')
            price = ad.get('price')
            safetyDeposit = ad.get('safetyDeposit')
            agencyRentalFee = ad.get('agencyRentalFee')
            surfaceArea = ad.get('surfaceArea')
            roomsQuantity = ad.get('roomsQuantity')
            energyClassification = ad.get('energyClassification')
            thumbnailUrl = ad.get('photos')[0].get('url')
            url = "https://www.bienici.com/annonce/location/tours/appartement/" + id

            banned_word = generate_variations("colocation") + generate_variations(
                "coloc") + generate_variations("colocataire") + ["résidence étudiante"]
            if (mots_absents(description, banned_word)):
                if not check_if_ad_already_saved(connection, id):
                    new_ads.append(insert_new_rent_ad(connection, id, title, description, price, safetyDeposit,
                                   agencyRentalFee, surfaceArea, roomsQuantity, energyClassification, thumbnailUrl, url))
            else:
                print(f"Annonce {url} contient des mots interdits")
        return new_ads
    else:
        print(f"Erreur : {response.status_code}")


def generate_variations(word):
    return [word.upper(), word.capitalize(), word + 's', word]


def check_for_new_ads(connection):

    if connection is None:
        return

    new_ads = []
    new_ads += get_bienIci_ads(connection)
    new_ads += get_seLoger_ads(connection)

    return new_ads


def get_seLoger_data_from_page(page_id=1) -> dict | None:
    """Return the data from the SeLoger website."""

    # get the page
    response = requests.get(
        "https://www.seloger.com/immobilier/locations/immo-tours-37/bien-appartement/?LISTING-LISTpg="+page_id,
        cookies=cookies,
        headers=headers,
    )

    if response.status_code == 200:

        # Utilise BeautifulSoup pour analyser l'HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        script_tags = soup.find_all('script')

        # Utilise une regex pour extraire le contenu JSON du script avec 'window["initialData"]'
        for script in script_tags:
            if 'window["initialData"]' in script.text:
                script_jsons = re.search(
                    r'window\["initialData"\]\s*=\s*JSON\.parse\("(.*?)"\);', script.text)

                if script_jsons:
                    # Décoder le contenu JSON encodé
                    json_str = script_jsons.group(1)
                    json_str = json_str.encode(
                        'utf-8').decode('unicode_escape')

                    # Charger la chaîne JSON en tant que dictionnaire Python
                    datasets = json.loads(json_str)

                    # Extraire les informations des cartes
                    cards = []
                    for card in datasets["cards"]["list"]:
                        if card["cardType"] == "classified":
                            cards.append(card)

                    # Récupérer les méta-données de navigation
                    search_meta = datasets["navigation"]

                    return {"results": cards, "search": search_meta}

        print("Aucun script avec 'window[\"initialData\"]' n'a été trouvé.")
    return None


def get_seLoger_data() -> dict | None:
    """Return the data from the SeLoger website."""

    datas = []

    # number of page
    response = requests.get(
        "https://www.seloger.com/immobilier/locations/immo-tours-37/bien-appartement",
        cookies=cookies,
        headers=headers,
    )

    if response.status_code == 200:

        # Utilise BeautifulSoup pour analyser l'HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        script_tags = soup.find_all('script')

        # Utilise une regex pour extraire le contenu JSON du script avec 'window["initialData"]'
        for script in script_tags:
            if 'window["initialData"]' in script.text:
                script_jsons = re.search(
                    r'window\["initialData"\]\s*=\s*JSON\.parse\("(.*?)"\);', script.text)

                if script_jsons:
                    # Décoder le contenu JSON encodé
                    json_str = script_jsons.group(1)
                    json_str = json_str.encode(
                        'utf-8').decode('unicode_escape')

                    # Charger la chaîne JSON en tant que dictionnaire Python
                    datasets = json.loads(json_str)

                    # Récupérer les méta-données de navigation
                    search_meta = datasets["navigation"]
                    nb_ads = search_meta["counts"]["count"]
                    nb_page = nb_ads // 25 + 1

    for page_id in range(1, nb_page + 1):
        data = get_seLoger_data_from_page(page_id)
        
        if data:
            datas += data["results"]

    return {"results": datas, "search": search_meta}


def get_seLoger_ads(connection):
    new_ads = []
    datas = get_seLoger_data()
    datas = datas["results"]

    for data in datas:
        new_ad = {
            "id": data['id'],
            "title": data['title'],
            "description": data['description'],
            "price": int(data['pricing']['rawPrice']),
            "safetyDeposit": None,
            "agencyRentalFee": None,
            "surfaceArea": data['surface'],
            "roomsQuantity": data['rooms'],
            "energyClassification": data['epc'],
            "thumbnailUrl": f"https://v.seloger.com/s/cdn/x/visuels{data['photos'][0]}" if len(data['photos']) > 0 else None,
            "url": "https://seloger.com" + data['classifiedURL']
        }

        # chek if price is under the limit
        if new_ad["price"] <= PRICE_LIMIT:
            if not check_if_ad_already_saved(connection, new_ad["id"]) & True:
                # check if ad have the right energy classification
                if data["epc"] in ENERGY_CLASSIFICATION:

                    banned_word = generate_variations("colocation") + generate_variations("coloc") + generate_variations("colocataire") + ["résidence étudiante"]
                    if (mots_absents(new_ad["description"], banned_word)):
                        
                        # get safetyDeposit and agencyRentalFee
                        other_data = get_seLoger_ad_info(new_ad["url"])
                        new_ad["safetyDeposit"] = round(other_data["props"]["pageProps"]["listingData"] ["listing"]["listingDetail"]["listingPrice"]["alur"]["garantieLocation"])
                        new_ad["agencyRentalFee"] = round(other_data["props"]["pageProps"]["listingData"]["listing"]["listingDetail"]["listingPrice"]["alur"]["honorairesLocataire"])

                        new_ads.append(new_ad)
                        insert_new_rent_ad(connection, new_ad["id"], new_ad["title"], new_ad["description"], new_ad["price"], new_ad["safetyDeposit"], new_ad["agencyRentalFee"], new_ad["surfaceArea"], new_ad["roomsQuantity"], new_ad["energyClassification"], new_ad["thumbnailUrl"], new_ad["url"])
                    else:
                        if DEBUG:
                            print(f"Annonce {new_ad['url']} contient des mots interdits")
                else:
                    if DEBUG:
                        print("dpe too high",
                          new_ad["energyClassification"], new_ad["url"])
            else:
                if DEBUG:
                    print("alreadt in db", new_ad["url"])
        else:
            if DEBUG:
                print("price too high", new_ad["price"], new_ad["url"])

    return new_ads


def get_seLoger_ad_info(new_ad_url):

    response = requests.get(new_ad_url, cookies=cookies, headers=headers)
    if response.status_code == 200:
        # Utilise BeautifulSoup pour analyser l'HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        rawData = soup.find('script', {'id': '__NEXT_DATA__'}).text

        # Charger la chaîne JSON en tant que dictionnaire Python
        data = json.loads(rawData)

        return data

    return None


if __name__ == '__main__':
    connection = create_connection()
    print(len(get_seLoger_ads(connection)))
