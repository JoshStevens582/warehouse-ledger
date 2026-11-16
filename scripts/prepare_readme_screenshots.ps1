# Seeds a paid order for supervisor screenshots (idempotent enough for local dev).
$ErrorActionPreference = "Stop"
$base = "http://127.0.0.1:8080/api"
$login = Invoke-RestMethod -Method POST -Uri "$base/auth/login" -ContentType "application/json" `
    -Body '{"email":"supervisor@example.com","password":"supervisor123"}'
$h = @{ Authorization = "Bearer $($login.access_token)" }
$products = Invoke-RestMethod -Uri "$base/products" -Headers $h
$productId = $products[0].id
$order = Invoke-RestMethod -Method POST -Uri "$base/orders" -Headers $h -ContentType "application/json" `
    -Body (@{
        customer_email = "buyer@example.com"
        lines          = @(@{ product_id = $productId; quantity = 4; unit_price = "50.00" })
    } | ConvertTo-Json -Depth 5)
$oid = $order.id
try {
    $checkout = Invoke-RestMethod -Method POST -Uri "$base/orders/$oid/checkout" -Headers $h
    Invoke-RestMethod -Method POST -Uri "$base/orders/$oid/record-test-payment" -Headers $h | Out-Null
} catch {
    Invoke-RestMethod -Method POST -Uri "$base/orders/$oid/record-test-payment" -Headers $h | Out-Null
}
$receiver = Invoke-RestMethod -Method POST -Uri "$base/auth/login" -ContentType "application/json" `
    -Body '{"email":"receiver@example.com","password":"receiver123"}'
$rh = @{ Authorization = "Bearer $($receiver.access_token)"; "Content-Type" = "application/json" }
Invoke-RestMethod -Method POST -Uri "$base/movements" -Headers $rh `
    -Body (@{ product_id = $productId; quantity_delta = 25 } | ConvertTo-Json) | Out-Null
Write-Output "paid_order_id=$oid"