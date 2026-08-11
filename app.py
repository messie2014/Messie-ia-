import os

from flask import Flask, render_template, jsonify


app = Flask(
    __name__,
    template_folder="templates"
)


@app.route("/")
def index():

    return render_template("index.html")


@app.route("/health")
def health():

    return jsonify({
        "status": "ok",
        "app": "Messie IA"
    })


@app.route("/debug-files")
def debug_files():

    base = os.path.dirname(
        os.path.abspath(__file__)
    )

    templates = os.path.join(
        base,
        "templates"
    )

    index_file = os.path.join(
        templates,
        "index.html"
    )

    return jsonify({

        "app": "Messie IA",

        "base_directory": base,

        "files": os.listdir(base),

        "templates_exists":
            os.path.isdir(templates),

        "templates_files":
            (
                os.listdir(templates)
                if os.path.isdir(templates)
                else []
            ),

        "index_exists":
            os.path.isfile(index_file)

    })


if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            "5000"
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )



