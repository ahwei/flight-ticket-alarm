# Flight Ticket Alarm

## Start the Project

### Using Docker

1. Build the Docker image and start the container:

   ```sh
   docker-compose up --build
   ```

2. The project will run at `http://localhost:5000`.

### Using Vercel

1. Deploy the project to Vercel:

   ```sh
   vercel
   ```

2. The project will run at the URL provided by Vercel.

## API

### `GET /`

Returns a JSON message.

#### Response

```json
{
  "message": "Hello, World!"
}
```
