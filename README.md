# UniversalPDF

Converta TXT, imagens (PNG/JPG), DOCX e PDF para PDF — via interface gráfica ou linha de comando.

---

## 🚀 Para Usuários Finais — Download Rápido

### Windows — Executável Pronto (Recomendado)

**Forma mais rápida: download direto**

1. Acesse: **[github.com/Ryan-nextLvl/MetPdf/releases](https://github.com/Ryan-nextLvl/MetPdf/releases)**
2. Baixe o arquivo **`UniversalPDF.exe`** da versão mais recente
3. Clique em **`UniversalPDF.exe`** para abrir — **sem instalação, sem Python, sem dependências extras**
4. Pronto! A interface gráfica aparece em segundos

**Como usar:**
- Arraste arquivos ou pastas para a janela
- Escolha o diretório de saída
- Clique em **Converter →** e acompanhe o progresso
- Cancele a qualquer momento com o botão **Cancelar**
- Ao fim, clique em **📂 Abrir pasta** para ver os PDFs gerados

**Requisitos:**
- Windows 7 ou superior
- Para converter `.docx`: Microsoft Word ou LibreOffice instalado (opcional — outros formatos funcionam sem)

**Dica — Acesso rápido:**
- Clique com botão direito no `UniversalPDF.exe` → **Enviar para → Área de Trabalho (criar atalho)**
- Ou arraste para a barra de tarefas para fixar

---

## 🔧 Para Desenvolvedores — Instalar do Código-Fonte

### Recomendado — `uv` (mais rápido)

```bash
# 1. Clonar o repositório
git clone https://github.com/Ryan-nextLvl/MetPdf.git
cd MetPdf

# 2. Instalar uv (uma vez)
# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
# Linux / macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Criar virtualenv e instalar dependências
uv venv .venv
uv pip install -r requirements.txt --python .venv

# 4. Ativar virtualenv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

# 5. Rodar a GUI
python gui.py
```

### Manual — pip

```bash
git clone https://github.com/Ryan-nextLvl/MetPdf.git
cd MetPdf
pip install -r requirements.txt
python gui.py
```

> **Windows + DOCX:** o `docx2pdf` requer o Microsoft Word instalado.  
> **Linux/macOS + DOCX:** instale o LibreOffice (`sudo apt install libreoffice` ou `brew install libreoffice`).

---

## 📖 Como Usar

### Interface Gráfica (GUI)

```bash
python gui.py
```

**Fluxo:**
1. Arraste arquivos ou pastas para a janela (ou clique nos botões **+ Arquivos** / **+ Pasta**)
2. Escolha o diretório de saída
3. Clique em **Converter →**
4. Acompanhe o progresso em tempo real
5. Cancele a qualquer momento com o botão **Cancelar**
6. Ao fim, clique em **📂 Abrir pasta de saída** para ver os PDFs

### Linha de Comando (CLI)

```bash
# Arquivo único
python main.py documento.docx

# Vários arquivos
python main.py arquivo1.txt arquivo2.png arquivo3.jpg

# Diretório inteiro
python main.py input/

# Varredura recursiva de subpastas
python main.py input/ --recursive

# Diretório de saída personalizado
python main.py input/ --output resultados/

# Log detalhado
python main.py input/ --verbose
```

---

## 📋 Formatos Suportados

| Extensão | Estratégia |
|----------|-----------|
| `.txt` | reportlab — preserva quebras de linha, layout A4 |
| `.png` `.jpg` `.jpeg` | Pillow + reportlab — centralizado, proporção mantida |
| `.docx` | docx2pdf (Word no Windows, LibreOffice no Unix) |
| `.pdf` | PyMuPDF — validação e cópia |

---

## 🏗️ Arquitetura

A conversão é centralizada em `core/service.py`. Tanto a GUI quanto a CLI usam o mesmo `ConversionService`, sem duplicação de lógica.

```
GUI (gui.py)  ──┐
                ├──► ConversionService ──► Dispatcher ──► Converters
CLI (main.py) ──┘
```

### Estrutura do Projeto

```
universalpdf/
├── gui.py                   # Interface gráfica (customtkinter)
├── main.py                  # CLI
├── requirements.txt
├── pyproject.toml
├── universalpdf.spec             # Configuração PyInstaller
├── generate_icon.py         # Geração do ícone .ico
├── converters/
│   ├── base.py              # Classe abstrata BaseConverter
│   ├── txt_converter.py     # TXT → PDF (reportlab)
│   ├── image_converter.py   # PNG/JPG → PDF (Pillow + reportlab)
│   ├── docx_converter.py    # DOCX → PDF (docx2pdf com subprocess worker)
│   └── pdf_converter.py     # PDF → validação + cópia (PyMuPDF)
├── core/
│   ├── dispatcher.py        # Roteador: escolhe o conversor pelo formato
│   ├── service.py           # ConversionService — backend compartilhado
│   └── exceptions.py        # Hierarquia de exceções
├── utils/
│   └── file_utils.py        # Helpers de caminho e coleta de arquivos
├── .github/
│   └── workflows/
│       └── release.yml      # GitHub Actions: compila .exe automaticamente
├── assets/
│   └── icon.ico             # Ícone da aplicação
├── input/                   # Pasta de entrada padrão
└── output/                  # PDFs gerados
```

---

## 🔌 API para Desenvolvedores

Use `ConversionService` em seus próprios scripts:

```python
from core.service import ConversionService
from pathlib import Path

service = ConversionService(output_dir=Path("output"))

def progresso(done, total, result):
    status = "OK" if result.success else f"FALHOU: {result.error}"
    print(f"[{done}/{total}] {result.input_path.name} — {status}")

results = service.convert_files(
    files=[Path("documento.txt"), Path("foto.png")],
    on_progress=progresso,
)
```

Para rodar em background (como a GUI faz):

```python
service.convert_files(files, on_progress=..., on_done=..., threaded=True)
```

Para cancelar:

```python
service.cancel()  # interrompe a fila após o arquivo atual
```

---

## ➕ Adicionar um Novo Conversor

1. Crie `converters/meu_formato_converter.py` estendendo `BaseConverter`:

```python
from pathlib import Path
from converters.base import BaseConverter

class MeuFormatoConverter(BaseConverter):
    def convert(self, input_path: Path, output_path: Path) -> None:
        self._ensure_output_dir(output_path)
        # lógica de conversão aqui
```

2. Registre a extensão em `core/dispatcher.py` (na função `_registry()`):

```python
from converters.meu_formato_converter import MeuFormatoConverter

def _registry() -> dict:
    return {
        # ...
        ".meuformato": MeuFormatoConverter,
    }
```

Pronto — GUI e CLI passam a reconhecer o novo formato automaticamente.

---

## 🔨 Para Desenvolvedores — Gerar Executável

```bash
/build
```

Ou manualmente:

```bash
python generate_icon.py          # gera assets/icon.ico
uv pip install pyinstaller --python .venv
.venv\Scripts\python -m PyInstaller universalpdf.spec --noconfirm
```

O executável fica em `dist/UniversalPDF.exe`.

---

## 🚀 CI/CD — Releases Automáticas

Ao criar uma git tag (`v1.0.0`, `v1.1.0`, etc.), o GitHub Actions compila automaticamente o `.exe` e publica um Release:

```bash
git tag v0.2.0
git push origin main --tags
```

Acesse **[github.com/Ryan-nextLvl/MetPdf/releases](https://github.com/Ryan-nextLvl/MetPdf/releases)** para baixar.

---

## 📝 Licença

MIT License — veja o arquivo `LICENSE` para detalhes.
