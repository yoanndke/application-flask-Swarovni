import hashlib
import os
from flask import Flask, flash, request, url_for, redirect, render_template, g, session
import sqlite3
from datetime import timedelta
from werkzeug.utils import secure_filename
import pandas as pd

app = Flask(__name__)
app.config['SECRET_KEY'] = 'Le$CPqtaWQ^#dCyegYBoa%%W5'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30) #Durée maximale d'une session
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 #Taille des images
app.config['UPLOAD_EXTENSIONS'] = ['.jpg', '.png'] #Permet de vérifier l'extension des images lorsque l'on ajoute ou modifie un produit
app.config['UPLOAD_PATH'] = 'static/img_product/' #Chemin des images à ajouter ou modifier lors de la publication d'un produit

#Création et connexion à la base de donnée 'ecommerce.db'
def connect_db():
    sql = sqlite3.connect('ecommerce.db')
    c = sql.cursor()

    #Création de la table utilisateurs puis de la table produits
    c.execute('''CREATE TABLE IF NOT EXISTS users ([id] INTEGER PRIMARY KEY AUTOINCREMENT, [firstname] TEXT, [name] TEXT,
                [mail] TEXT not null, [password] TEXT not null, [admin] INTEGER not null, [sex] TEXT, [phone_number] TEXT, 
                [address] TEXT, [postal_code] TEXT, [town] TEXT)
    ''')
    c.execute('''CREATE TABLE IF NOT EXISTS products 
                ([id] INTEGER PRIMARY KEY AUTOINCREMENT, [title] TEXT not null, [desc] TEXT, [price] DECIMAL(18, 2) not null,
                [tag] TEXT, [filename1] TEXT, [filename2] TEXT, [filename3] TEXT)
    ''')

    #Insertion de l'administrateur principal
    cur = c.execute('select * from users')
    results = cur.fetchall()
    if len(results) == 0:
        c.execute('insert into users (firstname, name, mail, password, admin) values (?, ?, ?, ?, ?)',
                    ['admin', 'admin', 'admin@admin.fr', make_hashes('admin'), 1])

    # Insertion des produits
    cur = c.execute('select * from products')
    results = cur.fetchall()
    if len(results) == 0:
        df = pd.read_csv('/Users/yoann/Desktop/Python/Flask/Projet Final/Scrapping données/products.csv', sep=';')
        cols = ",".join([str(i) for i in df.columns.tolist()])
        for index, row in df.iterrows():
            c.execute('insert into products (title, desc, price, tag, filename1, filename2, filename3) values (?, ?, ?, ?, ?, ?, ?)',
                        [row[0], row[1], round(float(row[2].replace(' EUR', '').replace(',', '.'))*2.2, 2), "bague",
                         row[3].replace(' - ', '-').replace(' ', '_'), row[4].replace(' - ', '-').replace(' ', '_'),
                         row[5].replace(' - ', '-').replace(' ', '_')])

    sql.row_factory = sqlite3.Row
    return sql

def get_db():
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

#Hash le password
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

#vérifier si les hashs des 2 password sont les mêmes
def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return hashed_text
    return False


#Page d'Accueil
@app.route('/', methods=['POST', 'GET'])
def index():
    if 'cart' not in session:
        session['cart'] = []
    db = get_db()
    cur = db.execute('select * from products') #Recherche de tous les produits dans notre BDD
    res_products = cur.fetchall()
    return render_template("home.html", rows_products=res_products) #Renvoie home.html + tous les produits de notre BDD

#Page de la catégories "Bague"
@app.route('/rings', methods=['POST', 'GET'])
def rings():
    db = get_db()
    cur = db.execute('select * from products where tag=(?)', ("bague",)) #Recherche de tous les bagues dans notre BDD
    res_rings = cur.fetchall()
    return render_template("rings.html", rows_rings=res_rings) #Renvoie rings.html + tous les bagues de notre BDD


#Page de Création du compte
@app.route('/sign_up', methods=['POST', 'GET'])
def sign_up():
    if request.method == 'POST':
        firstname = request.form['firstname'].capitalize() #récupère le champ du prénom
        name = request.form['name'].capitalize() #récupère le champ du nom
        mail = request.form['mail'] #récupère le champ de l'email
        password = request.form['password'] #récupère le champ du mot de passe
        sess_perm = request.form.getlist('sess_perm') #récupère la chackbox pour garder la session ouverte

        db = get_db()
        cur = db.execute('select * from users')
        results = cur.fetchall()

        mail_exist = False
        for row in results:
            if row[3] == mail:
                mail_exist = True
        if mail_exist == True: #on recherche si l'email est déjà utilisé, s'il existe on le dirige vers la page de connexion
            print("L'adresse email existe déjà dans notre BDD, veuillez vous connecter")
            return render_template('login.html')
        else:
            db = get_db()
            db.execute('insert into users (firstname, name, mail, password, admin) values (?, ?, ?, ?, ?)',
                        [firstname, name, mail, make_hashes(password), 0]) #sinon on l'inscrit
            db.commit()
            print('Tu es inscrit')
            session["users"] = { #on créé une session avec ses identifiants
                'firstname': firstname,
                'mail': mail,
                'admin': 0
            }
            session.permanent = False
            if len(sess_perm) == 1: #Si il a cliqué la chackbox pour garder sa session ouverte alors la session est permanente
                session.permanent = True
            print(session)
            return redirect(url_for('index'))
    else:
        return render_template('sign_up.html')

#Page uniquement accessible par les administrateurs permettant d'ajouter un nouvel admin
@app.route('/add_admin', methods=['POST', 'GET'])
def add_admin():
    if session["users"]["admin"] == 1: #si la session actuelle est un admin
        if request.method == 'POST':
            firstname = request.form['firstname'].capitalize()
            name = request.form['name'].capitalize()
            mail = request.form['mail']
            password = request.form['password']

            db = get_db()
            db.execute('insert into users (firstname, name, mail, password, admin) values (?, ?, ?, ?, ?)',
                       [firstname, name, mail, password, 1]) #on ajoute le nouvel administrateur à la BDD
            db.commit()
            return redirect(url_for('panel_admin'))
        else:
            return render_template('add_admin.html')
    else:
        return redirect('404.html') #sinon on retourne une 404

#Page de connexion
@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        session.clear() #on supprime la session actuelle
        mail = request.form['mail']
        password = request.form['password']
        sess_perm = request.form.getlist('sess_perm')

        db = get_db()
        cur = db.execute('select * from users')
        results = cur.fetchall()
        if len(results) == 0: #si aucun utilisateur existe dans notre BDD
            return render_template('sign_up.html') #on renvoie l'utilisateur à la page d'inscription
        else:
            hashed_pswd = make_hashes(password)
            for row in results:
                if row[3] == mail and row[4] == hashed_pswd: #Si l'email et le mot de passe existe dans une ligne de notre BDD
                    session["users"] = { #on crée sa session
                        'firstname': row[1],
                        'mail': row[3],
                        'admin': row[5]
                    }
                    session.permanent = False
                    if len(sess_perm) == 1:
                        session.permanent = True #session permanente si il a coché la checkbox "Garder ma Session Ouverte"
                    print(session)
                    return redirect(url_for('index'))
            else:
                flash('⚠ Email ou mot de passe incorrect') #s'il se trompe dans l'email ou le mot de passe, on affiche ce message
                return render_template('login.html')
    else:
        return render_template('login.html')

#Suppression d'un utilisateur
@app.route('/del_user', methods=['POST', 'GET'])
def del_user():
    if request.method == 'POST':
        if request.form['mail'] == '': #si le champ est vide
            flash("⚠ Veuillez ajouter l'email de l'utilisateur à supprimer")
            return render_template('del_user.html')
        else:
            mail = request.form['mail']
            db = get_db()
            cur = db.execute("select mail from users where mail = (?)", (mail,)) #chercher l'email dans la BDD
            results = cur.fetchall()
            if len(results) == 0: #si l'email n'existe pas dans la BDD
                flash("⚠ {} est inconnu".format(mail))
                return render_template('del_user.html')
            else:
                db.execute("delete from users where mail = ?", (mail,)) #sinon on supprime l'utilisateur
                db.commit()
            return redirect(url_for('panel_admin'))
    else:
        return render_template("del_user.html")

#Panel Admin
@app.route('/panel_admin', methods=['POST', 'GET'])
def panel_admin():
    if session["users"]["admin"] == 1: #si la session ouverte est un admin
        db = get_db()
        cur = db.execute('select firstname, name, mail, password, admin, sex, '
                         'phone_number, address, postal_code, town from users') #chercher tous les utilisateurs
        res_users = cur.fetchall()

        cur = db.execute('select title, desc, price, tag, filename1, filename2, filename3 from products') #chercher tous les produits
        res_products = cur.fetchall()
        return render_template("panel_admin.html", rows_users=res_users, rows_products=res_products) #renvoyer les utilisateurs et les produits
    else:
        return redirect('404.html') #sinon on renvoie la page 404

#Déconnexion
@app.route('/logout', methods=['POST', 'GET'])
def logout():
    session.clear() #supprime la session actuelle = déconnexion
    return redirect(url_for('index'))

#Ajout d'un produit
@app.route('/add_product', methods=['POST', 'GET'])
def add_product():
    if request.method == 'POST':
        lst_filename = []
        title = request.form['title']
        desc = request.form['desc']
        price = float(request.form['price'])
        tag = request.form['tag']
        for uploaded_file in request.files.getlist('file'): #pour toutes les photos ajouter
            if uploaded_file.filename != '': #si la photo existe
                filename = secure_filename(uploaded_file.filename) #on regarde si le nom du fichier est sécurisé (avec des _ pour les espaces)
                if filename != '': #si le filename existe
                    file_ext = os.path.splitext(filename)[1] #on récupère l'extension du fichier
                    if file_ext not in app.config['UPLOAD_EXTENSIONS']: #on regarde si l'extension est valide
                        return "Invalid image", 400
                    lst_filename.append(filename) #on ajoute le nom du fichier à une liste contenant tous les noms de fichier
                    uploaded_file.save(os.path.join('static/img_product', filename)) #on télécharge la photo dans le dossier static/img_product

        db = get_db()
        if len(lst_filename) == 1: #on affiche seulement le nombre de photo que l'admin à ajouter
            db.execute(
                'insert into products (title, desc, price, tag, filename1) values (?, ?, ?, ?, ?)',
                [title, desc, price, tag, lst_filename[0]])
        elif len(lst_filename) == 2:
            db.execute(
                'insert into products (title, desc, price, tag, filename1, filename2) values (?, ?, ?, ?, ?, ?)',
                [title, desc, price, tag, lst_filename[0], lst_filename[1]])
        elif len(lst_filename) == 3:
            db.execute(
                'insert into products (title, desc, price, tag, filename1, filename2, filename3) values (?, ?, ?, ?, ?, ?, ?)',
                [title, desc, price, tag, lst_filename[0], lst_filename[1], lst_filename[2]])
        else: #si aucune photo n'a été choisi alors on lui retourne la même page avec un message
            flash("⚠ Ajoutez au minimum une photo")
            return render_template('add_product.html')
        db.commit()
        print('Produit ajouté')
        return redirect(url_for('index'))
    else:
        return render_template('add_product.html')

#Suppression d'un produit
@app.route('/del_product', methods=['POST', 'GET'])
def del_product():
    if request.method == 'POST':
        if request.form['title'] == '':
            return render_template('del_product.html')
        else:
            title = request.form['title']
            db = get_db()
            cur = db.execute("select title from products where title = (?)", (title,)) #on cherche le titre du produit dans la BDD
            results = cur.fetchall()
            if len(results) == 0:
                return render_template('del_product.html', message="{} n'existe pas".format(title))
            db.execute("delete from products where title = ?", (title,)) #suppression du produit de la BDD
            db.commit()
            return redirect(url_for('index'))
    else:
        return render_template("del_product.html")

#Affichage du produit
@app.route('/product_page/<int:product_id>', methods=['POST', 'GET'])
def product_page(product_id): #on récupère l'id du produit
    db = get_db()
    cur = db.execute("select * from products where id = (?)", (product_id,))
    res_product = cur.fetchone() #on récupère la première ligne
    return render_template('product_page.html', product=res_product) #on affiche la page avec les infos correspondant au produit

#Modification d'un produit
@app.route('/edit_product/<int:product_id>', methods=['POST', 'GET'])
def edit_product(product_id):
    lst_filename = []
    db = get_db()
    cur = db.execute("select * from products where id = (?)", (product_id,))
    res_product = cur.fetchall()
    if request.method == 'POST':
        title = request.form['title']
        desc = request.form['desc']
        price = float(request.form['price'])
        tag = request.form['tag']
        for uploaded_file in request.files.getlist('file'): #pour tous les fichiers uploadés
            if uploaded_file.filename != '': #s'il y a un nom de fichier
                filename = secure_filename(uploaded_file.filename) #on sécurise le fichier (avec des _ à la place d'espace)
                if filename != '': #s'il y a un nom de fichier
                    file_ext = os.path.splitext(filename)[1] #on sélectionne l'extension
                    if file_ext not in app.config['UPLOAD_EXTENSIONS']: #on vérifie la validité de l'extension
                        return "Invalid image", 400
                    lst_filename.append(filename) #on ajoute la photo à notre liste de photos
                    uploaded_file.save(os.path.join('static/img_product/', filename)) #on télécharge l'image dans notre dossier

        for row in res_product:
            if len(lst_filename) == 0: #si les images n'ont pas été choisis, on garde les mêmes et on met à jour le reste
                db.execute('''UPDATE products SET title = (?), desc = (?), price = (?), tag = (?) WHERE id = (?)''',
                           (title, desc, price, tag, product_id))
            elif len(lst_filename) == 1: #si une image a été choisis, on supprime les photos et on met tout à jour
                db.execute('''UPDATE products SET title = (?), desc = (?), price = (?), tag = (?), filename1 = (?), filename2 = (?), filename3 = (?) WHERE id = (?)''',
                           (title, desc, price, tag, lst_filename[0], None, None, product_id))
            elif len(lst_filename) == 2: #si deux images ont été choisis, on supprime les photos et on met tout à jour
                db.execute('''UPDATE products SET title = (?), desc = (?), price = (?), tag = (?), filename1 = (?), filename2 = (?), filename3 = (?) WHERE id = (?)''',
                           (title, desc, price, tag, lst_filename[0], lst_filename[1], None, product_id))
            else: #sinon on met tout à jour
                db.execute('''UPDATE products SET title = (?), desc = (?), price = (?), tag = (?), filename1 = (?), filename2 = (?), filename3 = (?)
                           WHERE id = (?)''',(title, desc, price, tag, lst_filename[0], lst_filename[1], lst_filename[2], product_id))
            db.commit()
            return redirect(url_for('product_page', product_id=product_id))
        else:
            return render_template('edit_product.html', product=res_product[0])
    else:
        return render_template('edit_product.html', product=res_product[0])

#Ajout d'un produit au panier
@app.route('/add_cart', methods=['POST', 'GET'])
def add_cart():
    if request.method == "POST":
        l = []
        size = request.form.get('size')
        product_id = request.form['product_id']
        if 'cart' not in session: #si le panier n'existe pas dans la session
            session["cart"] = [] #création du panier
        if session["cart"] == []: #sinon si le panier est vide
            session["cart"].append(list((int(product_id), int(size))))
            flash("Ce produit a été ajouté à votre panier")
        elif list((int(product_id), int(size))) in session["cart"]:  # si le produit que l'on veut mettre dans le panier est déjà dans la session
            flash("⚠ Vous avez déjà ce produit dans votre panier avec la même quantité")
        else:
            for row in session["cart"]: #pour un élément product_id/qty dans la session
                l.append(int(row[0]))
                if int(row[0]) == int(product_id): #si le product_id est déjà dans la session
                    row[1] = int(size) #remplacer l'ancienne quantité par la nouvelle
                    flash("La quantité à été modifiée")
            if int(product_id) not in l: #si le produit n'existe pas dans la session
                session["cart"].append(list((int(product_id), int(size)))) #l'ajouter
                flash("Ce produit a été ajouté à votre panier")
            session.modified = True
        print(session)
    return redirect(url_for('product_page', product_id=product_id)) #on retourne la page produit

#panier
@app.route('/cart', methods=['POST', 'GET'])
def cart():
    display_cart = []
    product_id = []
    total_cart = []
    db = get_db()
    cur = db.execute("select id from products")
    products_id = cur.fetchall()
    for row in session["cart"]:
        if int(row[0]) not in [int(id[0]) for id in products_id]: #si le produit n'est plus dans la BDD
            session["cart"].remove(row) #on supprime le produit du panier
    if 'cart' not in session or len(session["cart"]) == 0: #si le panier est vide ou inexistant
        print("Aucun article")
        return render_template('cart.html', message='Aucun article dans votre panier')
    else:
        for row in session["cart"]:
            display_cart.append(row) #on ajoute les produits_id/qty à la liste display_cart
        if len(display_cart) == 0: #si la liste est égale à 0
            return render_template('cart.html', message='Aucun article dans votre panier')
        else:
            for elem in display_cart:
                product_id.append(elem[0]) #on ajoute les produits_id à la liste product_id
            if len(product_id) == 1:
                product_id = str(tuple(product_id)).replace(",", "") #on remplace la liste par un tuple pour faciliter la requete en SQL (attention à supprimer la virgule si on a qu'un produit
            else:
                product_id = tuple(product_id) #on remplace la liste par un tuple pour faciliter la requete en SQL
            cur = db.execute("select * from products where id in {}".format(product_id))
            product_in_cart = cur.fetchall() #product_in_cart est la liste des infos des produits du panier
            for product in product_in_cart:
                for elem in display_cart:
                    if product['id'] == elem[0]: #si l'id du produit dans la BDD est le même que celui de l'id du produit dans la session
                        total_cart.append(float(product['price']*elem[1])) #alors on mutliplie le prix (BDD) par la quantié (session)
            total_cart = sum(total_cart) #on somme les prix de tous les produits pour connaître le prix du panier total
        return render_template('cart.html', product_in_cart=product_in_cart, qty=elem[1], total_cart=total_cart)

# Livraison
@app.route('/checkout/shipping', methods=['POST', 'GET'])
def shipping():
    #recalcul du panier comme précédemment
    display_cart = []
    product_id = []
    total_cart = []
    db = get_db()
    for row in session["cart"]:
        display_cart.append(row)  # on ajoute les produits_id/qty à une nouvelle liste
    if len(display_cart) == 0:  # si la liste est égale à 0
        return render_template('cart.html', message='Aucun article dans votre panier')
    else:
        for elem in display_cart:
            product_id.append(elem[0])
        if len(product_id) <= 1:
            product_id = str(tuple(product_id)).replace(",", "")
        else:
            product_id = tuple(product_id)
        cur = db.execute("select * from products where id in {}".format(product_id))
        product_in_cart = cur.fetchall()
        for product in product_in_cart:
            for elem in display_cart:
                if product['id'] == elem[0]:
                    total_cart.append(float(product['price'] * elem[1]))
        total_cart = sum(total_cart)

    cur = db.execute("select * from users where mail = (?)", (session["users"]["mail"],)) #on récupère les données de l'utilisateur
    res_user = cur.fetchone()
    if request.method == "POST":
        if request.form['sex'] == "Homme":
            sex = 'M'
        elif request.form['sex'] == "Femme":
            sex = 'F'
        else:
            sex = 'Undetermined'
        phone_number = request.form['phone']
        address = request.form['address'].title()
        postal_code = request.form['postal_code']
        town = request.form['town'].upper()
        db.execute('''UPDATE users SET sex = (?), phone_number = (?), address = (?), postal_code = (?), town = (?)
                   WHERE id = (?)''', (sex, phone_number, address, postal_code, town, res_user['id'])) #on met à jour la BDD avec les nouvelles infos client
        db.commit()
        return redirect(url_for('payment'))

    return render_template('shipping.html', user=res_user, product_in_cart=product_in_cart, qty=elem[1], total_cart=total_cart)

#Page de paiement (affiche le prix total, mais ne récupère pas les informations bancaires)
@app.route('/checkout/payment', methods=['POST', 'GET'])
def payment():
    # recalcul du panier comme précédemment
    display_cart = []
    product_id = []
    total_cart = []
    db = get_db()
    for row in session["cart"]:
        display_cart.append(row)  # on ajoute les produits_id/qty à une nouvelle liste
    if len(display_cart) == 0:  # si la liste est égale à 0
        return render_template('cart.html', message='Aucun article dans votre panier')
    else:
        for elem in display_cart:
            product_id.append(elem[0])
        if len(product_id) <= 1:
            product_id = str(tuple(product_id)).replace(",", "")
        else:
            product_id = tuple(product_id)
        cur = db.execute("select * from products where id in {}".format(product_id))
        product_in_cart = cur.fetchall()
        for product in product_in_cart:
            for elem in display_cart:
                if product['id'] == elem[0]:
                    total_cart.append(float(product['price'] * elem[1]))
        total_cart = sum(total_cart)
    cur = db.execute("select * from users where mail = (?)", (session["users"]["mail"],))
    res_user = cur.fetchone()
    return render_template('payment.html', user=res_user, product_in_cart=product_in_cart, qty=elem[1], total_cart=total_cart)

#Supprimer un produit du panier
@app.route('/del_product_cart', methods=['POST', 'GET'])
def del_product_cart():
    if request.method == "POST": #au clic sur le bouton
        product_id = int(request.form['product_id']) #on récupère l'id du produit à supprimer
    if 'cart' not in session:
        return render_template('cart.html', message='Aucun article dans votre panier')
    else:
        for row in session["cart"]:
            if int(row[0]) == product_id: #si l'un des id du produit correspond à un présent dans la session
                session["cart"].remove(row) #on supprime le produit de la session
        return redirect(url_for('cart')) #on rafraichit la page

#Page non créée
@app.route('/comingSoon', methods=['POST', 'GET'])
def comingSoon():
    return render_template('comingSoon.html')

#Page de remerciements
@app.route('/checkout/thankyou_page', methods=['POST', 'GET'])
def thankyou_page():
    session["cart"] = [] #Vider le panier à la fin de la commande
    return render_template('thankyou_page.html')

#Page d'erreur 404
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

#Page d'erreur si une photo est trop grande
@app.errorhandler(413)
def too_large(e):
    return "File is too large", 413

if __name__ == '__main__':
    app.run()
    #app.run(debug=True)