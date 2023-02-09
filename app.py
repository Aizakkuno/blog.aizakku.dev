import os
import string
import time

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

app = Flask(__name__)
app.config.update()

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
@json_key("url")
@json_key("description")
@json_key("content", max=1024**2)
def api_post(god_password, title, url, description, content):
    if god_password != GOD_PASSWORD:
        return {"text": "Unauthorized!", "error": "unauthorized"}, 403

    article = {"title": title,
               "url": url,
               # don't feel like grabbing the first paragraph of the article
               "description": description,
               "content": content,
               "timestamp": time.time()}

    db.articles.insert_one(article)

    return {"text": "Posted article.", "article": article}, 200


@app.route("/")
def template_articles():
    articles = list(db.articles.find({}))

    return render_template("articles.html", articles=articles)


@app.route("/<string:url>")
def template_article(url):
    url_validated = validate_key(url)
    if not url_validated is True:
        # i might update this error syetm later to display without using js to interpret it
        return redirect("/?error=" + url_validated["error"])

    url = url.lower()

    article = db.articles.find_one({"url": url})
    if not article:
        return redirect("/?error=no_article")

    return render_template("article.html", article=article)


if __name__ == "__main__":
    app.run()
