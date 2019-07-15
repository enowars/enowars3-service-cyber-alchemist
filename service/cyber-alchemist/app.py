from abc import ABC, abstractmethod
from base64 import b64encode, b64decode
from binascii import hexlify, unhexlify
from flask import Flask, make_response, redirect, render_template, request, send_from_directory, session, url_for
from functools import wraps
from hexdump import hexdump, restore
from os import remove
from pickle import dump, dumps, load
from random import Random
from string import ascii_letters
from textwrap import wrap
from urllib.parse import quote_plus, unquote

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024
app.config['RECIPE_DIRECTORY'] = app.root_path + '/recipes/'
app.config['RECIPE_EXTENSION'] = '.recipe'
app.secret_key = b'extremely_secure_key'
random = Random()

def deny_banned(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('banned', False):
            return redirect(url_for('banned'))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/banned", methods=['GET'])
def banned():
    if not session.get('banned', False):
        return redirect(url_for('index'))
    return render_template('banned.html')

@app.route("/", methods=['GET'])
@deny_banned
def index():
    return render_template('index.html')

@app.route("/recipes/create", methods=['GET'])
@deny_banned
def create_recipe():
    return render_template('create_recipe.html')

@app.route("/recipes/create", methods=['POST'])
@deny_banned
def create_recipe_action():
    recipe_name = request.form.get('name')
    if not recipe_name:
        recipe_name = ''.join(random.choice(ascii_letters) for i in range(random.randint(20,40)))
    elif len(recipe_name) > 40:
        return render_template('create_recipe.html', error = 'Recipe name can not be longer than 40 characters.')
    elif '/' in recipe_name:
        return render_template('create_recipe.html', error = 'Recipe name may not contain slashes', sanitized_name = recipe_name.replace('/', ''))
    return redirect(url_for('show_recipe', recipe_name=recipe_name))

@app.route('/recipes/import', methods=['GET'])
@deny_banned
def import_recipe():
    return render_template('import_recipe.html', extension = app.config['RECIPE_EXTENSION'])

@app.route('/recipes/import', methods=['POST'])
@deny_banned
def import_recipe_action():
    try:
        request.files
    except Exception:
        return render_template('import_recipe.html', error = 'The recipe exceeds the maximum file size of 1MB.')
    if 'recipe' not in request.files:
        return render_template('import_recipe.html', error = 'No recipe was uploaded.')
    file = request.files['recipe']
    filename = file.filename
    if not file or filename == '':
        return render_template('import_recipe.html', error = 'No recipe was uploaded.')
    if '/' in filename or '.' not in filename:
        return render_template('import_recipe.html', error = 'The filename of the recipe is not valid.')
    recipe_name, extension = tuple(filename.rsplit('.', 1))
    if extension != app.config['RECIPE_EXTENSION'][1:]:
        return render_template('import_recipe.html', error = 'The extension of the recipe is not valid.')
    try:
        recipe = load(file)
    except Exception:
        session['banned'] = True
        return redirect(url_for('banned'))
    if (
        not isinstance(recipe, Recipe)
        or set(vars(recipe)) != {'name', 'base_ingredient', 'ingredients', 'potion'}
        or recipe.name != recipe_name
        or len(recipe.name) > 40
    ):
        session['banned'] = True
        return redirect(url_for('banned'))
    recipe.save()
    return redirect(url_for('show_recipe', recipe_name=recipe_name))

@app.route("/recipes/list", methods=['GET'])
@deny_banned
def list_recipes():
    recipes = session.get('recipes', [])
    return render_template('list_recipes.html', recipes=recipes)

@app.route('/recipe/<recipe_name>', methods=['GET'])
@deny_banned
def show_recipe(recipe_name):
    recipes = session.get('recipes', [])
    if recipe_name not in recipes:
        recipes.append(recipe_name)
        session['recipes'] = recipes
    recipe = Recipe.get(recipe_name)
    for step, ingredient in enumerate(recipe.ingredients):
        try:
            recipe.potion = ingredient(*[p for p in [recipe.potion] if p])
        except Exception as e:
            return render_template("show_recipe.html", recipe = recipe, step_failed = step + 1, error = e)
    return render_template("show_recipe.html", recipe = recipe)

@app.route('/recipe/<recipe_name>', methods=['POST'])
@deny_banned
def put_base_ingredient(recipe_name):
    recipe = Recipe.get(recipe_name)
    if (request.form['base_ingredient'] != ""):
        base_ingredient = request.form['base_ingredient']
    else:
        base_ingredient = None
    recipe.base_ingredient = base_ingredient
    recipe.potion = base_ingredient
    recipe.save()
    return redirect(url_for('show_recipe', recipe_name=recipe_name))

@app.route('/recipe/<recipe_name>/export', methods=['GET'])
@deny_banned
def export_recipe(recipe_name):
    filename = recipe_name + app.config['RECIPE_EXTENSION']
    try:
        return send_from_directory(
            app.config['RECIPE_DIRECTORY'],
            filename=filename,
            as_attachment=True
        )
    except Exception:
        recipe = Recipe.get(recipe_name)
        response = make_response(dumps(recipe))
        response.headers.set('Content-Type', 'application/octet-stream')
        response.headers.set('Content-Disposition', 'attachment', filename=filename)
        return response

@app.route('/recipe/<recipe_name>/delete', methods=['GET'])
@deny_banned
def delete_recipe(recipe_name):
    recipes = session.get('recipes', [])
    if recipe_name in recipes:
        recipes.remove(recipe_name)
        session['recipes'] = recipes
    try:
        remove(app.config['RECIPE_DIRECTORY'] + '/' + recipe_name + app.config['RECIPE_EXTENSION'])
    except Exception:
        pass
    return redirect(url_for("list_recipes"))

@app.route('/recipe/<recipe_name>/<ingredient>/<method>', methods=['GET'])
@deny_banned
def put_ingredient(recipe_name, ingredient, method):
    recipe = Recipe.get(recipe_name)
    recipe.ingredients.append(getattr(globals()[ingredient], method))
    recipe.save()
    return redirect(url_for('show_recipe', recipe_name=recipe_name))

@app.route('/recipe/<recipe_name>/delete/<int:step>', methods=['GET'])
@deny_banned
def delete_ingredient(recipe_name, step):
    recipe = Recipe.get(recipe_name)
    del(recipe.ingredients[step - 1])
    recipe.save()
    return redirect(url_for('show_recipe', recipe_name=recipe_name))

@app.route('/recipe/<recipe_name>/move/<int:old_step>/<int:new_step>', methods=['GET'])
@deny_banned
def move_ingredient(recipe_name, old_step, new_step):
    recipe = Recipe.get(recipe_name)
    recipe.ingredients.insert(new_step - 1, recipe.ingredients.pop(old_step - 1))
    recipe.save()
    return redirect(url_for('show_recipe', recipe_name=recipe_name))

@app.route("/easter-egg", methods=['GET'])
@deny_banned
def easter_egg():
    return render_template('easter_egg.html')

@app.route("/accept-cookies", methods=['GET'])
@deny_banned
def accept_cookies():
    session['cookies-accepted'] = True
    return redirect(url_for('index'))

@app.context_processor
def cookies_accepted():
    return dict(cookies_accepted=session.get('cookies-accepted', False))

@app.errorhandler(404)
def error_404(e):
    return render_template('error_404.html'), 404

@app.template_filter('print_ingredient')
def print_ingredient(ingredient):
    return ingredient.__qualname__.replace('.', ' - ').title()

class Recipe:

    def __init__(self, name, base_ingredient=None, ingredients=None, potion=None):
        if ingredients is None:
            ingredients = []
        self.name = name
        self.base_ingredient = base_ingredient
        self.ingredients = ingredients
        self.potion = potion

    def save(self):
        path = app.config['RECIPE_DIRECTORY'] + self.name + app.config['RECIPE_EXTENSION']
        with open(path, 'wb') as f:
            dump(self, f)

    @classmethod
    def get(cls, name):
        path = app.config['RECIPE_DIRECTORY'] + name + app.config['RECIPE_EXTENSION']
        try:
            with open(path, 'rb') as f:
                return load(f)
        except Exception:
            return cls(name)

class base64(ABC):

    @abstractmethod
    def encode(input = ''):
        return b64encode(input.encode()).decode()

    @abstractmethod
    def decode(input = ''):
        return b64decode(input).decode()

class hex(ABC):

    @abstractmethod
    def encode(input = ''):
        return '0x' + hexlify(input.encode()).decode()

    @abstractmethod
    def decode(input = ''):
        if input[:2] == '0x':
            input = input[2:]
        return unhexlify(input.encode()).decode()

    @abstractmethod
    def dump(input=''):
        return hexdump(input.encode(), result='return')

    @abstractmethod
    def restore(input=''):
        return restore(input).decode()

class url(ABC):

    @abstractmethod
    def encode(input=''):
        return quote_plus(input)

    @abstractmethod
    def decode(input=''):
        return unquote(input)

class unicode(ABC):

    @abstractmethod
    def encode(input = ''):
        return '\\x'.join(wrap(hex.encode(input), 2))[2:]

    @abstractmethod
    def decode(input = ''):
        return hex.decode(''.join(input.split('\\x')))
