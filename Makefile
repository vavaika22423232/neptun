# Neptun — зручні цілі з кореня репозиторію
.PHONY: deploy-validate deploy-check photon-up help

help:
	@echo "make deploy-validate  — тести Python-воркера (перед деплоєм)"
	@echo "make deploy-check     — те саме"
	@echo "make photon-up        — запустити локальний Photon з infra/photon"
	@echo "Повний деплой на VPS:  bash deploy/deploy-from-mac.sh"
	@echo "З перебудовою gazetteer: REBUILD_GAZETTEER=1 bash deploy/deploy-from-mac.sh"

deploy-validate deploy-check:
	@bash deploy/validate-before-deploy.sh

photon-up:
	@cd infra/photon && docker compose up -d
