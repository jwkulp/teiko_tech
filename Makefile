.PHONY: setup pipeline dashboard

setup:
	python3 -m pip install -r requirements.txt

pipeline:
	python3 load_data.py
	python3 analysis/frequencies.py
	python3 analysis/stats.py
	python3 analysis/queries.py

dashboard:
	mkdir -p $(HOME)/.streamlit
	printf '[general]\nemail = ""\n' > $(HOME)/.streamlit/credentials.toml
	python3 -m streamlit run dashboard/app.py
