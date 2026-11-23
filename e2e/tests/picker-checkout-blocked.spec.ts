import { expect, test } from "@playwright/test";

test("picker cannot start Paystack checkout", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "picker", exact: true }).click();
  await page.getByRole("button", { name: /sign in/i }).click();
  await page.waitForSelector("main.dashboard");

  await expect(page.getByRole("heading", { name: "Customer order" })).toBeVisible();
  await expect(page.getByRole("button", { name: /Checkout \(Paystack\)/i })).toHaveCount(0);

  const checkoutStatus = await page.evaluate(async () => {
    const token = localStorage.getItem("token");
    if (!token) {
      throw new Error("No JWT in localStorage after sign-in");
    }

    const productsRes = await fetch("/api/products", {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!productsRes.ok) {
      throw new Error(`products: ${productsRes.status}`);
    }
    const products = (await productsRes.json()) as { id: number }[];
    const productId = products[0]?.id;
    if (productId === undefined) {
      throw new Error("No seeded products");
    }

    const orderRes = await fetch("/api/orders", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        customer_email: "picker-e2e@example.com",
        lines: [{ product_id: productId, quantity: 1, unit_price: "50.00" }],
      }),
    });
    if (!orderRes.ok) {
      throw new Error(`create order: ${orderRes.status}`);
    }
    const order = (await orderRes.json()) as { id: number };

    const checkoutRes = await fetch(`/api/orders/${order.id}/checkout`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    return checkoutRes.status;
  });

  expect(checkoutStatus).toBe(403);
});