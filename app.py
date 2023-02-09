import os
import string
import time

from datetime import datetime
from functools import wraps
from dotenv import load_dotenv

from flask import Flask, render_template, session, redirect, request
from pymongo import MongoClient

def session_key(key,
                min: int = 1,
                max: int = 4096,
                var_type: type = str,
                required: bool = True,
                printable: bool = True):

    def wrapper(f):
        @wraps(f)
        def wrapper_function(*args, **kwargs):
            if session:
                value = session.get(key)
                if not value and required:
                    return {"text": f"Please specify a value for '{key}'!",
                            "error": f"invalid_{key}"}, 400
                elif not required:
                    value = value or None
            else:
                if required:
                    return {"text": "Bad request!",
                            "error": "bad_request"}, 400
                else:
                    value = None

            if value:
                if not isinstance(value, var_type):
                    try:
                        value = var_type(value)
                    except ValueError:
                        return {"text": (f"Value for '{key}' must be type "
                                         f"{var_type.__name__}!"),
                                "error": f"invalid_{key}"}, 400

                if len(str(value)) < min:
                    return {"text": (f"Value for '{key}' must be at least "
                                     f"{min} characters!"),
                            "error": f"invalid_{key}"}, 400

                if len(str(value)) > max:
                    return {"text": (f"Value for '{key}' must be at most "
                                     f"{max} characters!"),
                            "error": f"invalid_{key}"}, 400

                if printable and isinstance(value, str):
                    for chr in value:
                        if chr not in string.printable:
                            return {"text": f"Value for '{key}' uses invalid characters!",
                                    "error": f"invalid_{key}"}, 400

            return f(**{key: value}, **kwargs)
        return wrapper_function
    return wrapper


def json_key(key,
             min: int = 1,
             max: int = 4096,
             var_type: type = str,
             required: bool = True,
             printable: bool = True):

    def wrapper(f):
        @wraps(f)
        def wrapper_function(*args, **kwargs):
            if request.json:
                value = request.json.get(key)
                if not value and required:
                    return {"text": f"Please specify a value for '{key}'!",
                            "error": f"invalid_{key}"}, 400
                elif not required:
                    value = value or None
            else:
                if required:
                    return {"text": "Bad request!",
                            "error": "bad_request"}, 400
                else:
                    value = None

            if value:
                if not isinstance(value, var_type):
                    try:
                        value = var_type(value)
                    except ValueError:
                        return {"text": (f"Value for '{key}' must be type "
                                         f"{var_type.__name__}!"),
                                "error": f"invalid_{key}"}, 400

                if len(str(value)) < min:
                    return {"text": (f"Value for '{key}' must be at least "
                                     f"{min} characters!"),
                            "error": f"invalid_{key}"}, 400

                if len(str(value)) > max:
                    return {"text": (f"Value for '{key}' must be at most "
                                     f"{max} characters!"),
                            "error": f"invalid_{key}"}, 400

                if printable and isinstance(value, str):
                    for chr in value:
                        if chr not in string.printable:
                            return {"text": f"Value for '{key}' uses invalid characters!",
                                    "error": f"invalid_{key}"}, 400

            return f(**{key: value}, **kwargs)
        return wrapper_function
    return wrapper


def validate_key(value,
                 key,
                 min: int = 1,
                 max: int = 4096,
                 var_type: type = str,
                 required: bool = True,
                 printable: bool = True):

    if not value and required:
        return {"text": f"Please specify a value for '{key}'!",
                "error": f"invalid_{key}"}, 400
    elif not required:
        value = value or None

    if value:
        if not isinstance(value, var_type):
            try:
                value = var_type(value)
            except ValueError:
                return {"text": (f"Value for '{key}' must be type "
                                    f"{var_type.__name__}!"),
                        "error": f"invalid_{key}"}, 400

        if len(str(value)) < min:
            return {"text": (f"Value for '{key}' must be at least "
                                f"{min} characters!"),
                    "error": f"invalid_{key}"}, 400

        if len(str(value)) > max:
            return {"text": (f"Value for '{key}' must be at most "
                                f"{max} characters!"),
                    "error": f"invalid_{key}"}, 400

        if printable and isinstance(value, str):
            for chr in value:
                if chr not in string.printable:
                    return {"text": f"Value for '{key}' uses invalid characters!",
                            "error": f"invalid_{key}"}, 400

    return True


load_dotenv()

GOD_PASSWORD = os.getenv("GOD_PASSWORD")

client = MongoClient('localhost', 27017)

db = client.blog_db

# i suggest adding error handlers for blank requests into apps, such as this one
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY"),
    TEMPLATES_AUTO_RELOAD=True
)

@app.route("/api/set-god-password", methods=["POST"])
@json_key("god_password")
def api_set_god_password(god_password):
    session["god_password"] = god_password

    return {"text": "Set your session's god password.",
            "god_password": god_password}, 200


@app.route("/post")
@session_key("god_password")
def template_post(god_password):
    if god_password != GOD_PASSWORD:
        return redirect("/?error=unauthorized")
    else:
        return render_template("post.html")


@app.route("/api/post", methods=["POST"])
@session_key("god_password")
@json_key("title")
@json_key("code")
@json_key("description")
@json_key("content", max=1024**2)
def api_post(god_password, title, code, description, content):
    if god_password != GOD_PASSWORD:
        return {"text": "Unauthorized!", "error": "unauthorized"}, 403

    if db.articles.find_one({"code": code}):
        return {"text": "Code exists!", "error": "code_exists"}, 409

    article = {"title": title,
               "code": code,
               "description": description,
               "content": content,
               "timestamp": int(time.time())}

    db.articles.insert_one(article)

    article.pop("_id")

    return {"text": "Posted article.", "article": article}, 200


@app.route("/")
def template_articles():
    articles = list(db.articles.find({}))

    return render_template("articles.html", articles=articles)


@app.route("/<string:code>")
def template_article(code):
    url_validated = validate_key(code, "code")
    if not url_validated is True:
        return redirect("/?error=" + url_validated["error"])

    code = code.lower()

    article = db.articles.find_one({"code": code})
    if not article:
        return redirect("/?error=no_article")

    date_time = datetime.fromtimestamp(article["timestamp"])
    formatted_time = date_time.strftime("%A, %d %B %Y")

    return render_template("article.html", article=article, formatted_time=formatted_time)


if __name__ == "__main__":
    app.run()
