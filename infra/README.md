# Infra

## RSSHub (flux TikTok)

Service Docker qui expose des flux RSS pour TikTok (et bien d'autres sources). Utilisé par l'onglet "TikTok" du dashboard pour récupérer les derniers Reels de `@beyond_the_hoop`.

### Setup initial sur la VM

```bash
ssh freebox@192.168.0.168
cd <chemin du repo>
docker compose -f infra/rsshub-docker-compose.yml up -d
```

### Vérifier que ça tourne

```bash
curl -s http://localhost:1200/tiktok/user/@beyond_the_hoop | head -20
```

Doit renvoyer du XML `<rss version="2.0">...`.

### Mise à jour de l'image

```bash
docker compose -f infra/rsshub-docker-compose.yml pull
docker compose -f infra/rsshub-docker-compose.yml up -d
```

### Logs

```bash
docker logs -f rsshub
```

### Configuration

L'instance est bindée sur `127.0.0.1:1200` uniquement (pas exposée sur le LAN). Le backend FastAPI tourne sur la même VM et accède à `http://localhost:1200/tiktok/user/@beyond_the_hoop`. La variable d'env `TIKTOK_RSS_URL` permet de pointer vers un autre endpoint en dev.
