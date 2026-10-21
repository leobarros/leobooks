# SQUEMA SQL

```sql
-- 1. Tabela de Livros
CREATE TABLE books (
    id VARCHAR(36) PRIMARY KEY, -- UUID v4 recomendado para facilidade de sync
    title VARCHAR(255) NOT NULL,
    authors TEXT NOT NULL, -- Lista formatada ou JSON string (ex: "Autor A, Autor B")
    publisher VARCHAR(150),
    isbn VARCHAR(20),
    total_pages INT NOT NULL DEFAULT 0,
    current_page INT NOT NULL DEFAULT 0,
    status VARCHAR(20) CHECK (status IN ('WANT_TO_READ', 'READING', 'READ', 'ABANDONED')) DEFAULT 'READING',
    cover_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Tabela de Notas, Resumos e Citações
CREATE TABLE notes (
    id VARCHAR(36) PRIMARY KEY,
    book_id VARCHAR(36) NOT NULL,
    type VARCHAR(20) CHECK (type IN ('QUOTE', 'SUMMARY', 'INSIGHT')) NOT NULL,
    content TEXT NOT NULL,
    page_number INT,
    chapter VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
);

-- 3. Tabela de Tags (Categorias Globais)
CREATE TABLE tags (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    color_hex VARCHAR(7) DEFAULT '#6C757D', -- Suporte a identificação visual no App
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Tabela Associativa M:N (Notas <-> Tags)
CREATE TABLE note_tags (
    note_id VARCHAR(36) NOT NULL,
    tag_id VARCHAR(36) NOT NULL,
    PRIMARY KEY (note_id, tag_id),
    FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);
```
