# Sheet Music Storage, Retrival and PDF Processing

Brasileiro is a full-stack web app which provides easy access to a large
database of sheet music.

It includes a PDF-processing engine which uses statistical learning
techniques to split large PDFs into indiviual songs, identify metadata,
and standardise the files for the backend.

## To run locally

1. Install docker: https://docs.docker.com/engine/install/
2. Run

```
docker compose build
docker compose up
```

![architecture](https://github.com/AmitaiRosenbaum/brasileiro/blob/33d9bc0da19f173d800e21ca3130c3c7984bcd71/public/architecture.png)
