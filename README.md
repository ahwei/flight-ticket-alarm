# Flight Ticket Alarm

## Start the Project

### Set Environment Variables

1. Copy the example environment file:

   ```sh
   cp env.example .env
   ```

2. Edit the `.env` file to include your API keys and secrets.

   - AMADEUS_API_KEY: [Get your Amadeus API Key](https://developers.amadeus.com/register)
   - AMADEUS_API_SECRET: [Get your Amadeus API Secret](https://developers.amadeus.com/register)
   - LINE_CHANNEL_ACCESS_TOKEN: [Get your LINE Channel Access Token](https://developers.line.biz/en/)
   - LINE_CHANNEL_SECRET: [Get your LINE Channel Secret](https://developers.line.biz/en/)

### Using Docker

1. Build the Docker image and start the container:

   ```sh
   docker-compose up --build
   ```

2. The project will run at `http://localhost:3310`.

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
