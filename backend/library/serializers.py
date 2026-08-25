from bson import ObjectId
def clean(doc):
    if not doc: return None
    d = dict(doc)
    d["id"] = str(d.pop("_id"))
    return d
