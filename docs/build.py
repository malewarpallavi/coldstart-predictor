import json, pathlib
here = pathlib.Path(__file__).parent
model = json.dumps(json.load(open(here.parent / "predictor" / "model.json")), separators=(",", ":"))
html = (here / "template.html").read_text().replace("/*MODEL_JSON*/", model)
(here / "index.html").write_text(html)
print("wrote docs/index.html", round(len(html) / 1024), "KB")
