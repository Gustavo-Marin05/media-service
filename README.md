# Media Service API

**Microservicio para subida y gestión de archivos multimedia**  
Usa **MinIO** como almacenamiento y **PostgreSQL** para metadatos.

---

## Características

- Subida de archivos (imágenes, videos, documentos)
- Almacenamiento en **MinIO** (S3 compatible)
- Metadatos en **PostgreSQL**
- URLs públicas directas
- Documentación con **Swagger UI**
- Consulta con **GraphQL**
- CORS habilitado
- Dockerizado con `docker-compose`

---

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET`  | `/health` | Health check |
| `POST` | `/media`  | Subir archivo |
| `GET`  | `/docs`   | **Swagger UI** |
| `POST` | `/graphql`| GraphQL (GraphiQL) |

---

## Tecnologías

- **Flask** (Python)
- **MinIO** (S3 storage)
- **PostgreSQL**
- **Flasgger** (Swagger/OpenAPI)
- **Strawberry** (GraphQL)
- **Docker + Docker Compose**

---

## Requisitos

- Docker
- Docker Compose
- (Opcional) Python 3.11 para desarrollo local

---

## Inicio Rápido (Docker)

```bash
# 1. Clonar el repositorio
git clone <tu-repo>
cd <tu-proyecto>

# 2. Levantar servicios
docker-compose up --build
