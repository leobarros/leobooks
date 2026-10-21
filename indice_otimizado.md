# Indices otimizados

```sql
-- Acelera a listagem de notas de um livro específico
CREATE INDEX idx_notes_book_id ON notes(book_id);

-- Otimiza a busca global de tags por nome
CREATE INDEX idx_tags_name ON tags(name);

-- Acelera consultas de notas por tipo (ex: listar apenas citações)
CREATE INDEX idx_notes_type ON notes(type);
```
