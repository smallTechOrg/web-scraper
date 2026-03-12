# web-scrapper-boilerplate-python

## Tech Stack

- [Flask](https://flask.palletsprojects.com/en/stable/) – For backend

## Features

- 


## Prerequisites

### Install Python 

   - [Windows](https://github.com/Madhyamakist/workspace-setup-windows) 
   - [macOS](https://github.com/Madhyamakist/workspace-setup-mac/blob/dev/python_installation.md)
   <!-- - [Linux](https://github.com/Madhyamakist/workspace-setup-windows/blob/dev/python_installation.md)   -->


### Python version control

#### macOS and Linux

<details>


The Python version needs to be the same as mentioned in the `.tool-versions` file.

Make sure the correct Python version has been set up using `asdf` before you work on this project.
```
python3 --version
```


</details>

#### Windows

<details>


- The Python version needs to be the same as mentioned in the `.python-version` file using pyenv-win.

- Make sure the correct Python version has been set by running `python --version`


</details>

---

## Getting Started

### Clone the repository:

```bash
git clone https://github.com/Madhyamakist/ai-agent-boilerplate.git myproject
```

---

### Set up virtual environment
#### Windows
<details>
- To create a virtual environment called "venv", run

```bash
python -m venv venv
```
-  To activate the environment
```bash
venv\Scripts\activate
```
</details>

#### macOS
<details>

- Create a virtual environment named "venv", 

```bash
python3 -m venv venv
```
-  To activate the environment
```bash
source venv/bin/activate
```
</details>

---

### Install dependencies and playwright
After activating your virtual environment, install dependencies by

Might take time to install

```bash
pip install -r requirements.txt
```
Install playwright using

```bash

python -m playwright install --with-deps chromium
```

## Run Flask to render frontend

### Setup Env

Cope `.env.example` into `.env` (gitignored).
```
cp .env.example .env
```

Replace the values (get it from team members?)
```
GROQ_API_KEY=randomstring
DATABASE_URL=postgresql://username:password@localhost:5432/
```


### Run

If virtual environment is activated and dependencies are installed then run chatbot by:

```bash
python app.py
```
Now visit http://127.0.0.1:5000/ in your browser.
For newer APIs visit http://127.0.0.1:5001/api/docs.

## Test Flask APIs 

If flask is rendered successfully, then test APIs by:

```bash
cd test
pytest --html=test_report.html --self-contained-html -v
```


## For Linting

Using ruff (example inside `code/`)
```
ruff check app.py --fix
```