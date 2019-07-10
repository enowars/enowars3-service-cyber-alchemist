# CyberAlchemist

Alias: **Remote-Code-Execution-as-a-Service / RCEaaS**

CTF-Challenge for ENOWARS 3 based on Python, Flask and Gunicorn.

The service allows to create "recipes" of en-/decoding steps to manipulate multiple inputs in the same way.
The idea is inspired by [CyberChef](https://gchq.github.io/CyberChef/).

## Vulnerabilities
- Operations are taken from string parameters and are blindly executed:
The line `recipe.ingredients.append(getattr(globals()[ingredient], method))` (see `service/cyber-alchemist/app.py`:164)
searches for `ingredient` in `globals()`, gets the attribute `method` from it and appends the reference to the function to ingredients.
This way, not only the intended ingredients can be executed, but all functions from all objects available in the scope of the app.

- Recipes can be imported as pickle files. [Pickle](https://docs.python.org/3/library/pickle.html) has known security issues with unserializing untrusted input.

## Exploits
All exploits are also implemented in `checker/checker.py`.

#### #1 Leak random state
Predict the output of the pseudorandom number generator:
1. Call `/recipe/<recipe_name>/random/getstate` to get the random state of the pseudorandom number generator in the potion field.
2. In the python exploit, create an own `r = random.Random()` object and set `r.setstate(<random_state>)` to the state you obtained from the recipe's potion field.
3. Execute `recipe_name = ''.join(r.choice(ascii_letters) for i in range(r.randint(20,40)))` (as often as you want) to predict future recipe names the server will generate.

#### #2 RCE via recipe ingredient
Include arbitrary functions in ingredients (even from packages which are not imported in `app.py`):
1. Craft malicious recipes by copying the app's recipe class and include arbitrary functions in ingredients, e.g. `subprocess.check_output`.
2. Import the recipe
3. Show the recipe and see the result in the potion field

####  #3 RCE via pickle import
1. Craft malicious pickle file (google "pickle RCE")
2. Import file
3. You get banned, so you have to pipe the results of your code execution to a file which is publicly available, e.g. in `static`. 

## Service
The service directory contains all source files needed to run CyberAlchemist.

### Development

#### With docker
http://localhost:8787 / http://[::1]:8787

    cd service
    docker-compose up -d

#### Without docker
http://localhost:5000

    cd service/cyber-alchemist
	FLASK_APP=app.py FLASK_DEBUG=1 python3 -m flask run
    
## Checker
The checker puts flags in all the team's vulnboxes, tests if they can be retrieved afterwards, and checks all other important functionality of the service.
Additionally, it contains an exploit function to test, whether the intended exploits are possible (only during testing, not during the actual ctf).

Run with `-h` to get the output.

### Development

#### With Docker

Checkout the branch `local`

    docker-compose up
   
Access http://[::1]:7878/

#### Without Docker
    
    python3 checker.py listen 666
    http://localhost:666/
    
    {
        "method":"putflag",
        "address": "localhost"
    }
    
    {
        "method":"getflag",
        "address": "localhost"
    }



We want to test the "live" configuration therefore we want to access the service container from "outside" through the exposed port `8787`. Checker and service are running on the docker host and are accessible through the host gateway. Use `docker inspect *service_container_id*` to get the IP of the gateway. Use the IP as address (instead of "gunicorn") in the checker web interface.

    {
        "method": "putflag",
        "address": "gunicorn"
    }

### Production

    docker network create checkernet --ipv6 --subnet fd00:1337:0:cecc::/64 --gateway fd00:1337:0:cecc::ffff
    docker-compose up -d