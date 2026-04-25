# AI Council Mobile

Expo React Native app for running AI Council on iPhone.

## Local iPhone Setup

1. Install dependencies:

   ```powershell
   cd C:\Users\sina_\OneDrive\Desktop\Council\ai-empire\apps\mobile
   npm install
   ```

2. Start the API so your iPhone can reach it on your Wi-Fi:

   ```powershell
   cd C:\Users\sina_\OneDrive\Desktop\Council\ai-empire
   python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8001
   ```

3. Create a local mobile env file:

   ```powershell
   copy .env.example .env.local
   ```

   Confirm the value matches your computer LAN IP:

   ```env
   EXPO_PUBLIC_API_URL=http://192.168.1.101:8001
   ```

4. Start Expo:

   ```powershell
   npm run start
   ```

5. Install **Expo Go** on your iPhone, scan the QR code, and run the app.

## Notes

- Your iPhone and computer must be on the same Wi-Fi network.
- If your computer IP changes, update `.env.local`.
- If LAN mode does not connect, try `npm run start:tunnel`.
