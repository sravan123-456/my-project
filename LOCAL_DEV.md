# Local development (Docker)

1. Install and start **Docker Desktop**.
2. From `my-project/` run:

   ```powershell
   .\scripts\deploy-local.ps1
   ```

3. Open **http://localhost:8080** and log in with your committee credentials.

## Dynamic UPI QR (test flow)

1. **Committee Admin** → **UPI Payment QR Code** → enter committee **UPI ID** (e.g. `9876543210@ybl`) → **Save payment settings**.
2. **Donations** → **Add Donation** → enter donor name and amount → choose **UPI**.
3. A **Scan to pay (amount included)** QR appears; scan with PhonePe / GPay / Paytm to verify the amount is pre-filled.
4. After payment, save the donation (optional UPI transaction ID).

## Stop local stack

```powershell
docker compose -f docker-compose.yml -f docker-compose.local.yml down
```

## Promote to production

When satisfied locally, push `main` and let GitHub Actions deploy, or SSH to the VM and run `scripts/deploy.sh`.
