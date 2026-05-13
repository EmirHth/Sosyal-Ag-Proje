from __future__ import annotations

from flask import Flask, render_template, request

from recommender import DEFAULT_CREATOR_DATASET, recommend_influencers_from_dataset


app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    product = ""
    top_k = 5
    result = None
    error = None

    if request.method == "POST":
        product = (request.form.get("product") or "").strip()
        top_k = int(request.form.get("top_k") or 5)

        if not product:
            error = "Urun adini girmen gerekiyor."
        else:
            try:
                result = recommend_influencers_from_dataset(
                    dataset_path=DEFAULT_CREATOR_DATASET,
                    product_query=product,
                    top_k=top_k,
                )
            except Exception as exc:
                error = str(exc)

    return render_template(
        "index.html",
        product=product,
        top_k=top_k,
        result=result,
        error=error,
        dataset_path=str(DEFAULT_CREATOR_DATASET),
    )


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
