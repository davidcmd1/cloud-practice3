
import os
import sqlite3
import datetime

from flask import Flask, request, jsonify
from flask_cors import CORS
from functools import wraps


# CONFIGURACION
DB_PATH = "catalog.db"
API_KEY = os.environ.get("API_KEY", "devkey")

app = Flask(__name__)
CORS(app)


# CONEXION A SQLITE
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# CREAR BASE DE DATOS
def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL NOT NULL CHECK(price >= 0),
                stock INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
        """)


# SEGURIDAD CON API KEY
def require_key(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        key = request.headers.get("X-API-KEY")

        if key != API_KEY:
            return jsonify({"error": "Unauthorized"}), 401

        return func(*args, **kwargs)

    return wrapper


# GET - CONSULTAR TODOS LOS PRODUCTOS
@app.route("/products", methods=["GET"])
@require_key
def get_products():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM products ORDER BY id"
        ).fetchall()

    return jsonify([dict(row) for row in rows]), 200


# GET - CONSULTAR PRODUCTO POR ID
@app.route("/products/<int:product_id>", methods=["GET"])
@require_key
def get_product(product_id):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM products WHERE id = ?",
            (product_id,)
        ).fetchone()

    if row is None:
        return jsonify({"error": "Product not found"}), 404

    return jsonify(dict(row)), 200


# POST - CREAR PRODUCTO
@app.route("/products", methods=["POST"])
@require_key
def create_product():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    name = data.get("name")
    price = data.get("price")
    stock = data.get("stock", 0)

    if not name or price is None:
        return jsonify({
            "error": "name and price are required"
        }), 400

    created_at = datetime.datetime.now().isoformat()

    try:
        with get_db() as conn:
            cursor = conn.execute(
                """
                INSERT INTO products
                (name, price, stock, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (name, price, stock, created_at)
            )

            product_id = cursor.lastrowid

            row = conn.execute(
                "SELECT * FROM products WHERE id = ?",
                (product_id,)
            ).fetchone()

        return jsonify(dict(row)), 201

    except (sqlite3.IntegrityError, TypeError, ValueError):
        return jsonify({
            "error": "Invalid product data"
        }), 400


# PUT - ACTUALIZAR PRODUCTO
@app.route("/products/<int:product_id>", methods=["PUT"])
@require_key
def update_product(product_id):
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    with get_db() as conn:
        product = conn.execute(
            "SELECT * FROM products WHERE id = ?",
            (product_id,)
        ).fetchone()

        if product is None:
            return jsonify({
                "error": "Product not found"
            }), 404

        name = data.get("name", product["name"])
        price = data.get("price", product["price"])
        stock = data.get("stock", product["stock"])

        try:
            conn.execute(
                """
                UPDATE products
                SET name = ?, price = ?, stock = ?
                WHERE id = ?
                """,
                (name, price, stock, product_id)
            )

            updated = conn.execute(
                "SELECT * FROM products WHERE id = ?",
                (product_id,)
            ).fetchone()

        except (sqlite3.IntegrityError, TypeError, ValueError):
            return jsonify({
                "error": "Invalid product data"
            }), 400

    return jsonify(dict(updated)), 200


# DELETE - ELIMINAR PRODUCTO
@app.route("/products/<int:product_id>", methods=["DELETE"])
@require_key
def delete_product(product_id):
    with get_db() as conn:
        product = conn.execute(
            "SELECT * FROM products WHERE id = ?",
            (product_id,)
        ).fetchone()

        if product is None:
            return jsonify({
                "error": "Product not found"
            }), 404

        conn.execute(
            "DELETE FROM products WHERE id = ?",
            (product_id,)
        )

    return jsonify({
        "message": "Product deleted"
    }), 200


# INICIALIZAR SQLITE PARA RENDER Y EJECUCION LOCAL
init_db()


# EJECUTAR SERVIDOR LOCAL
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))

    app.run(
        host="0.0.0.0",
        port=port
    )
