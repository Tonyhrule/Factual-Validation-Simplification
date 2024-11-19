from helpers.data import save_file, stringify
from helpers.pc import query_index

results = query_index("a", "pubmed_summarized", top_k=10000, include_vector=True)

save_file(
    "data/pubmed_summarized.json",
    stringify(list(map(lambda x: {"id": x.id, "vector": x.values}, results.matches))),
)
