from bert_score import score

candidates = ["日本狼曾分布于日本的本州、四国和九州，但已于1905年灭绝。"]
references = ["本州、四国及九州。"]

P, R, F1 = score(candidates, references, model_type="bert-base-uncased")


print(f"BERT Precision: {P.mean().item():.4f}")
print(f"BERT Recall: {R.mean().item():.4f}")
print(f"BERT F1 Score: {F1.mean().item():.4f}")
