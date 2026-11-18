import { FormEvent, useEffect, useState } from "react";

type Product = { id: number; sku: string; name: string; shelf_quantity: number };
type Role = "receiver" | "picker" | "supervisor";
type Movement = {
  id: number;
  product_id: number;
  quantity_delta: number;
  order_id: number | null;
  created_at: string;
};
type OrderDetail = {
  id: number;
  customer_email: string;
  status: string;
  currency: string;
  total_amount: string;
  paystack_reference: string | null;
};

function statusPillClass(status: string | null): string {
  if (!status) return "status-pill status-pill--other";
  if (status === "paid") return "status-pill status-pill--paid";
  if (status === "pending_payment") return "status-pill status-pill--pending";
  return "status-pill status-pill--other";
}

const API = "/api";

const STORAGE_TOKEN = "token";
const STORAGE_ROLE = "warehouse_role";
const STORAGE_EMAIL = "warehouse_email";
const STORAGE_ACTIVE_ORDER = "warehouse_active_order_id";

function orderIdFromReference(reference: string): number | null {
  const match = /^wh-(\d+)-/.exec(reference);
  if (!match) return null;
  const id = Number(match[1]);
  return Number.isFinite(id) ? id : null;
}

function orderIdFromReturnUrl(): number | null {
  const params = new URLSearchParams(window.location.search);
  const fromQuery = params.get("warehouse_order");
  if (fromQuery && !Number.isNaN(Number(fromQuery))) {
    return Number(fromQuery);
  }
  const reference = params.get("reference") ?? params.get("trxref");
  if (reference) {
    return orderIdFromReference(reference);
  }
  return null;
}

function persistActiveOrderId(orderId: number | null) {
  if (orderId === null) {
    sessionStorage.removeItem(STORAGE_ACTIVE_ORDER);
    return;
  }
  sessionStorage.setItem(STORAGE_ACTIVE_ORDER, String(orderId));
}

function readPersistedOrderId(): number | null {
  const raw = sessionStorage.getItem(STORAGE_ACTIVE_ORDER);
  if (!raw) return null;
  const id = Number(raw);
  return Number.isFinite(id) ? id : null;
}

const DEMO_ACCOUNTS: { email: string; password: string; role: Role; hint: string }[] = [
  {
    email: "receiver@example.com",
    password: "receiver123",
    role: "receiver",
    hint: "Add stock (Delivery)",
  },
  {
    email: "picker@example.com",
    password: "picker123",
    role: "picker",
    hint: "Remove stock for orders",
  },
  {
    email: "supervisor@example.com",
    password: "supervisor123",
    role: "supervisor",
    hint: "View only",
  },
];

function roleFromToken(token: string): Role | null {
  try {
    const payload = JSON.parse(atob(token.split(".")[1] ?? "")) as { role?: Role };
    return payload.role ?? null;
  } catch {
    return null;
  }
}

function readStoredRole(token: string | null): Role | null {
  const stored = localStorage.getItem(STORAGE_ROLE);
  if (stored === "receiver" || stored === "picker" || stored === "supervisor") {
    return stored;
  }
  return token ? roleFromToken(token) : null;
}

export default function App() {
  const [email, setEmail] = useState("receiver@example.com");
  const [password, setPassword] = useState("receiver123");
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(STORAGE_TOKEN));
  const [role, setRole] = useState<Role | null>(() =>
    readStoredRole(localStorage.getItem(STORAGE_TOKEN)),
  );
  const [signedInEmail, setSignedInEmail] = useState(
    () => localStorage.getItem(STORAGE_EMAIL) ?? "",
  );
  const [products, setProducts] = useState<Product[]>([]);
  const [delta, setDelta] = useState(10);
  const [productId, setProductId] = useState<number | "">("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [orderBusy, setOrderBusy] = useState(false);
  const [activeOrderId, setActiveOrderId] = useState<number | null>(null);
  const [customerEmail, setCustomerEmail] = useState("buyer@example.com");
  const [recentMovements, setRecentMovements] = useState<Movement[]>([]);
  const [recentLoadProblem, setRecentLoadProblem] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [dbInfo, setDbInfo] = useState<{
    database_host: string;
    database_port: number;
    database_name: string;
    stock_movement_rows: number;
    order_rows: number;
  } | null>(null);
  const [orderStatus, setOrderStatus] = useState<string | null>(null);
  const [orderDetail, setOrderDetail] = useState<OrderDetail | null>(null);
  const [receiptBody, setReceiptBody] = useState<string | null>(null);
  const [lookupOrderId, setLookupOrderId] = useState("");
  const [recentOrders, setRecentOrders] = useState<
    { id: number; status: string; total_amount: string }[]
  >([]);

  function logout() {
    localStorage.removeItem(STORAGE_TOKEN);
    localStorage.removeItem(STORAGE_ROLE);
    localStorage.removeItem(STORAGE_EMAIL);
    setToken(null);
    setRole(null);
    setSignedInEmail("");
    setProducts([]);
    setError("");
    setProductId("");
    setActiveOrderId(null);
    setLookupOrderId("");
    setOrderDetail(null);
    setOrderStatus(null);
    setReceiptBody(null);
    persistActiveOrderId(null);
    setRecentMovements([]);
    setSuccessMessage("");
  }

  function adoptWorkingOrder(orderId: number, message?: string) {
    setActiveOrderId(orderId);
    setLookupOrderId(String(orderId));
    persistActiveOrderId(orderId);
    if (message) {
      setSuccessMessage(message);
    }
    void refreshOrderStatus(orderId);
  }

  async function loadDbInfo() {
    const res = await fetch(`${API}/health`);
    if (!res.ok) return;
    const data = (await res.json()) as {
      database_host: string;
      database_port: number;
      database_name: string;
      stock_movement_rows: number;
      order_rows: number;
    };
    setDbInfo(data);
  }

  async function loadRecentMovements(bearer: string) {
    const res = await fetch(`${API}/movements/recent`, {
      headers: { Authorization: `Bearer ${bearer}` },
    });
    if (!res.ok) {
      setRecentMovements([]);
      setRecentLoadProblem(
        res.status === 404
          ? "Recent list needs a restarted API (stop uvicorn, start it again on port 8080)."
          : `Could not load movements (${res.status}).`,
      );
      return;
    }
    setRecentLoadProblem("");
    const data = (await res.json()) as Movement[];
    setRecentMovements(data);
  }

  async function loadRecentOrders(bearer: string) {
    const res = await fetch(`${API}/orders?limit=15`, {
      headers: { Authorization: `Bearer ${bearer}` },
    });
    if (!res.ok) {
      setRecentOrders([]);
      return;
    }
    const data = (await res.json()) as { id: number; status: string; total_amount: string }[];
    setRecentOrders(data);
  }

  async function loadProducts(bearer: string) {
    const res = await fetch(`${API}/products`, {
      headers: { Authorization: `Bearer ${bearer}` },
    });
    if (res.status === 401) {
      logout();
      throw new Error("Session expired. Sign in again.");
    }
    if (!res.ok) throw new Error("Failed to load products");
    const data = (await res.json()) as Product[];
    setProducts(data);
    if (data.length > 0) setProductId(data[0].id);
  }

  function prependMovement(saved: Movement) {
    setRecentMovements((prev) => {
      const rest = prev.filter((m) => m.id !== saved.id);
      return [saved, ...rest].slice(0, 15);
    });
    setRecentLoadProblem("");
  }

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    void loadProducts(token)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
    void loadRecentMovements(token);
    void loadDbInfo();
    if (role === "picker" || role === "supervisor") {
      void loadRecentOrders(token);
    }
  }, [token, role]);

  useEffect(() => {
    if (!token) return;
    const fromPaystack = orderIdFromReturnUrl();
    if (fromPaystack !== null) {
      adoptWorkingOrder(
        fromPaystack,
        `Returned from Paystack for order #${fromPaystack}. Confirming payment with Paystack…`,
      );
      void confirmPayment(fromPaystack);
      const clean = window.location.pathname === "/" ? "/" : "/";
      window.history.replaceState({}, "", clean);
      return;
    }
    const stored = readPersistedOrderId();
    if (stored !== null && activeOrderId === null) {
      setLookupOrderId(String(stored));
      void (async () => {
        const ok = await refreshOrderStatus(stored, { quietMissing: true });
        if (ok) {
          setActiveOrderId(stored);
        } else {
          setLookupOrderId("");
          persistActiveOrderId(null);
        }
      })();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- run once per sign-in / Paystack return
  }, [token]);

  async function onLogin(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await fetch(`${API}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        setError("Login failed. Check email and password.");
        return;
      }
      const data = (await res.json()) as { access_token: string; role: Role };
      localStorage.setItem(STORAGE_TOKEN, data.access_token);
      localStorage.setItem(STORAGE_ROLE, data.role);
      localStorage.setItem(STORAGE_EMAIL, email);
      setToken(data.access_token);
      setRole(data.role);
      setSignedInEmail(email);
      void loadRecentMovements(data.access_token);
      void loadDbInfo();
    } finally {
      setLoading(false);
    }
  }

  function fillDemo(account: (typeof DEMO_ACCOUNTS)[number]) {
    setEmail(account.email);
    setPassword(account.password);
    setError("");
  }

  async function confirmPayment(orderId: number) {
    if (!token) return;
    setError("");
    setSuccessMessage("");
    setOrderBusy(true);
    try {
      const res = await fetch(`${API}/orders/${orderId}/sync-payment`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      const body = (await res.json().catch(() => ({}))) as { detail?: string; status?: string };
      if (!res.ok) {
        const detail = body.detail ?? "Could not confirm payment";
        setError(
          detail.includes("reference")
            ? `${detail} Use Checkout (Paystack) on this order first, complete Success, then Confirm payment.`
            : detail,
        );
        return;
      }
      setSuccessMessage(`Payment confirmed for order #${orderId} (${body.status ?? "ok"}).`);
      await refreshOrderStatus(orderId);
      await loadRecentOrders(token);
    } finally {
      setOrderBusy(false);
    }
  }

  async function refreshOrderStatus(
    orderId: number,
    options?: { quietMissing?: boolean },
  ): Promise<boolean> {
    if (!token) return false;
    if (!options?.quietMissing) {
      setError("");
    }
    setOrderBusy(true);
    try {
      const res = await fetch(`${API}/orders/${orderId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const body = (await res.json().catch(() => ({}))) as OrderDetail & { detail?: string };
      if (!res.ok) {
        if (res.status === 404) {
          setActiveOrderId(null);
          setOrderDetail(null);
          setOrderStatus(null);
          setReceiptBody(null);
          persistActiveOrderId(null);
          if (!options?.quietMissing) {
            const ids = recentOrders.map((o) => o.id).join(", ");
            setError(
              ids
                ? `No order #${orderId} in the database. Existing orders: ${ids}. Use Create order for a new id (do not type the next number).`
                : `No order #${orderId}. Use Create order — Postgres assigns the id.`,
            );
            void loadRecentOrders(token);
          }
          return false;
        }
        const detail =
          typeof body.detail === "string"
            ? body.detail
            : `Could not load order #${orderId} (${res.status}).`;
        setError(detail);
        setOrderDetail(null);
        setReceiptBody(null);
        return false;
      }
      const status = body.status ?? "unknown";
      setOrderStatus(status);
      setOrderDetail({
        id: body.id ?? orderId,
        customer_email: body.customer_email,
        status,
        currency: body.currency,
        total_amount: String(body.total_amount),
        paystack_reference: body.paystack_reference ?? null,
      });
      await loadReceipt(orderId, token, status);
      return true;
    } finally {
      setOrderBusy(false);
    }
  }

  async function loadReceipt(orderId: number, authToken: string, status: string) {
    if (status !== "paid") {
      setReceiptBody(null);
      return;
    }
    const res = await fetch(`${API}/orders/${orderId}/receipt`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    if (res.status === 404) {
      setReceiptBody("Queued. The worker writes one receipt. Click Refresh.");
      return;
    }
    if (!res.ok) {
      setReceiptBody(null);
      return;
    }
    const data = (await res.json()) as { body?: string };
    setReceiptBody(data.body ?? null);
  }

  async function openExistingOrder(orderId: number) {
    setActiveOrderId(orderId);
    setLookupOrderId(String(orderId));
    persistActiveOrderId(orderId);
    await refreshOrderStatus(orderId);
  }

  async function loadOrderFromField() {
    const parsed = Number(lookupOrderId);
    if (!Number.isFinite(parsed) || parsed < 1) {
      setError("Enter an order id from the list, or click Create order.");
      return;
    }
    await openExistingOrder(parsed);
  }

  function handleCheckoutClick() {
    if (payOrderId === null) {
      setError(
        "No order selected. Click order #2 in the table above, or enter 2 and click Load, then try Checkout again.",
      );
      return;
    }
    void startPaystackCheckout(payOrderId);
  }

  async function startPaystackCheckout(orderId: number) {
    if (!token) return;
    setError("");
    setSuccessMessage("Opening Paystack…");
    setOrderBusy(true);
    try {
      const res = await fetch(`${API}/orders/${orderId}/checkout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const body = (await res.json().catch(() => ({}))) as { detail?: string };
        setSuccessMessage("");
        setError(body.detail ?? "Checkout failed — is PAYSTACK_SECRET_KEY in .env? Restart API after editing.");
        return;
      }
      const data = (await res.json()) as { authorization_url: string; reference: string };
      persistActiveOrderId(orderId);
      const paystackTab = window.open(data.authorization_url, "_blank", "noopener,noreferrer");
      if (!paystackTab) {
        setSuccessMessage(
          `Popup blocked. Taking you to Paystack for order #${orderId} in this tab…`,
        );
        window.location.assign(data.authorization_url);
        return;
      }
      setSuccessMessage(
        `Paystack opened in a new tab for order #${orderId}. Pay there, then come back and click Confirm payment.`,
      );
      await refreshOrderStatus(orderId);
    } catch {
      setSuccessMessage("");
      setError(
        "Could not reach the API. Is it running on port 8080? Is this page served from Vite (e.g. localhost:5173)?",
      );
    } finally {
      setOrderBusy(false);
    }
  }

  async function createOrderForPick() {
    if (!token || productId === "" || delta < 1) return;
    setError("");
    setOrderBusy(true);
    try {
      const res = await fetch(`${API}/orders`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          customer_email: customerEmail,
          lines: [
            {
              product_id: productId,
              quantity: delta,
              unit_price: "50.00",
            },
          ],
        }),
      });
      if (!res.ok) {
        const body = (await res.json().catch(() => ({}))) as { detail?: string };
        setError(body.detail ?? "Could not create order");
        return;
      }
      const data = (await res.json()) as { id: number };
      adoptWorkingOrder(data.id);
      setOrderStatus("pending_payment");
      void loadRecentOrders(token);
      setSuccessMessage(
        role === "picker"
          ? `Created order #${data.id}. Pick (−) or Pay with Paystack below.`
          : `Created order #${data.id}. Pay with Paystack below.`,
      );
    } finally {
      setOrderBusy(false);
    }
  }

  async function recordMovement(sign: 1 | -1) {
    if (!token || productId === "") return;
    if (sign < 0 && role === "picker" && activeOrderId === null) {
      setError("Create an order first, then pick against that order.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const body: {
        product_id: number;
        quantity_delta: number;
        order_id?: number;
      } = {
        product_id: productId,
        quantity_delta: sign * delta,
      };
      if (sign < 0 && activeOrderId !== null) {
        body.order_id = activeOrderId;
      }
      const res = await fetch(`${API}/movements`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const errBody = (await res.json().catch(() => ({}))) as { detail?: string };
        setError(errBody.detail ?? "Movement rejected");
        setSuccessMessage("");
        return;
      }
      const saved = (await res.json()) as Movement;
      prependMovement(saved);
      const orderPart = saved.order_id != null;
      setSuccessMessage(
        sign > 0
          ? `Delivery recorded (+${saved.quantity_delta}). Shelf total updated.`
          : `Pick recorded (${saved.quantity_delta})${orderPart ? ` for order #${saved.order_id}` : ""}.`,
      );
      if (sign < 0 && role === "picker") {
        const fulfilled = activeOrderId;
        setActiveOrderId(null);
        setSuccessMessage(`Order #${fulfilled} picked. Inventory updated.`);
      }
      await Promise.all([loadProducts(token), loadRecentMovements(token), loadDbInfo()]);
    } finally {
      setLoading(false);
    }
  }

  const canDeliver = role === "receiver";
  const canPick = role === "picker";

  const payOrderId = activeOrderId;

  if (!token) {
    return (
      <div className="app">
        <header className="topbar topbar--login">
          <span className="brand">
            <span className="brand-mark">WL</span>
            Warehouse Ledger
          </span>
        </header>
        <main className="login-shell">
        <div className="login-wrap">
          <div className="login-card">
            <h1>Sign in</h1>
            <p className="login-tagline">
              Inventory and order management with a live ledger-backed stock count.
            </p>
            <form onSubmit={onLogin} className="login-form">
              <label className="field">
                <span>Email</span>
                <input
                  type="email"
                  autoComplete="username"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </label>
              <label className="field">
                <span>Password</span>
                <input
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </label>
              <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
                {loading ? "Signing in…" : "Sign in"}
              </button>
            </form>
            {error && <p className="alert alert-error">{error}</p>}
            <div className="eval-accounts">
              <p className="eval-label">Evaluation accounts</p>
              <div className="eval-grid">
                {DEMO_ACCOUNTS.map((account) => (
                  <button
                    key={account.email}
                    type="button"
                    className="eval-chip"
                    onClick={() => fillDemo(account)}
                    title={account.hint}
                  >
                    {account.role}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
        </main>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-left">
          <span className="brand">
            <span className="brand-mark">WL</span>
            Warehouse Ledger
          </span>
          {role && <span className={`role-badge role-${role}`}>{role}</span>}
        </div>
        <div className="topbar-right">
          {signedInEmail && <span className="user-email">{signedInEmail}</span>}
          <button type="button" className="btn btn-ghost" onClick={logout}>
            Log out
          </button>
        </div>
      </header>

      <main className="dashboard">
        {dbInfo && (
          <section className="panel panel-subtle sync-panel">
            <h2 className="sync-panel-title">PostgreSQL source of truth</h2>
            <p className="sync-panel-body">
              This UI reads <strong>{dbInfo.database_name}</strong> on{" "}
              <strong>
                {dbInfo.database_host}:{dbInfo.database_port}
              </strong>
              . In pgAdmin, connect to that exact database and refresh the grid.
            </p>
            <ul className="sync-panel-list">
              <li>
                <strong>{dbInfo.order_rows}</strong> rows in <code>orders</code> (checkout list should
                match)
              </li>
              <li>
                <strong>{dbInfo.stock_movement_rows}</strong> rows in <code>stock_movements</code>{" "}
                (Activity + shelf totals — not the same as orders)
              </li>
            </ul>
            <p className="muted sync-panel-hint">
              Running <code>pytest</code> without <code>warehouse_ledger_test</code> used to wipe this
              database; that is now blocked. If counts still differ, you are usually in the wrong DB in
              pgAdmin or an old grid tab.
            </p>
          </section>
        )}
        <section className="panel">
          <div className="panel-head">
            <h2>Inventory</h2>
            <p className="muted">On-hand quantity derived from the movement ledger</p>
          </div>
          {loading && products.length === 0 ? (
            <p className="muted">Loading…</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>SKU</th>
                    <th>Name</th>
                    <th className="num">On shelf</th>
                  </tr>
                </thead>
                <tbody>
                  {products.map((p) => (
                    <tr key={p.id}>
                      <td className="sku-cell">{p.sku}</td>
                      <td>{p.name}</td>
                      <td
                        className={`num shelf-qty${p.shelf_quantity < 0 ? " shelf-qty--negative" : ""}`}
                      >
                        {p.shelf_quantity}
                        {p.shelf_quantity < 0 && (
                          <span className="shelf-warn"> — add stock as receiver</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {role === "picker" && (
          <section className="panel">
            <div className="panel-head">
              <h2>Customer order</h2>
              <p className="muted">
                Create or select an order, then pick stock below. Payment is handled by a supervisor.
              </p>
            </div>
            <div className="movement-form">
              <label className="field field-inline">
                <span>Product</span>
                <select
                  value={productId}
                  onChange={(e) => setProductId(Number(e.target.value))}
                  aria-label="Product for order"
                >
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.sku}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field field-inline">
                <span>Qty</span>
                <input
                  type="number"
                  min={1}
                  value={delta}
                  onChange={(e) => setDelta(Number(e.target.value))}
                />
              </label>
              <label className="field field-inline">
                <span>Customer email</span>
                <input
                  type="email"
                  value={customerEmail}
                  onChange={(e) => setCustomerEmail(e.target.value)}
                />
              </label>
              <button
                type="button"
                className="btn btn-primary"
                disabled={orderBusy || productId === "" || delta < 1}
                onClick={() => createOrderForPick()}
              >
                {orderBusy && payOrderId === null
                  ? "Creating…"
                  : payOrderId !== null
                    ? "New order"
                    : "Create order"}
              </button>
            </div>
            <div className="workflow-card">
              {payOrderId !== null ? (
                <p className="order-meta">
                  Picking for order <strong>#{payOrderId}</strong>
                  {orderStatus ? (
                    <>
                      {" "}
                      — <span className={statusPillClass(orderStatus)}>{orderStatus.replaceAll("_", " ")}</span>
                    </>
                  ) : null}
                </p>
              ) : (
                <p className="muted">Create an order or select one from the list to enable Pick / ship.</p>
              )}
              {recentOrders.length > 0 && (
                <div className="table-wrap recent-orders-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Order</th>
                        <th>Status</th>
                        <th className="num">Total (ZAR)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {recentOrders.map((o) => (
                        <tr
                          key={o.id}
                          className={payOrderId === o.id ? "recent-order-row--active" : "recent-order-row"}
                          onClick={() => void openExistingOrder(o.id)}
                        >
                          <td>#{o.id}</td>
                          <td>
                            <span className={statusPillClass(o.status)}>{o.status.replaceAll("_", " ")}</span>
                          </td>
                          <td className="num">{o.total_amount}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              <div className="movement-form" style={{ marginTop: "0.75rem" }}>
                <label className="field field-inline">
                  <span>Order ID</span>
                  <input
                    type="number"
                    min={1}
                    value={lookupOrderId}
                    aria-label="Order ID"
                    onChange={(e) => setLookupOrderId(e.target.value)}
                    placeholder="From table"
                  />
                </label>
                <button
                  type="button"
                  className="btn btn-ghost"
                  style={{ color: "var(--text)", border: "1px solid var(--border)" }}
                  disabled={orderBusy || lookupOrderId.trim() === ""}
                  onClick={() => void loadOrderFromField()}
                >
                  Load
                </button>
              </div>
              {successMessage && <p className="alert alert-success">{successMessage}</p>}
              {error && <p className="alert alert-error">{error}</p>}
            </div>
          </section>
        )}

        {role === "supervisor" && (
          <div className="dashboard-grid dashboard-grid--split">
          <section className="panel">
            <div className="panel-head">
              <h2>Orders & checkout</h2>
              <p className="muted">
                <strong>Create order</strong> adds a new row and Postgres picks the id. Then checkout and confirm
                payment.
              </p>
            </div>
            <div className="movement-form">
              <label className="field field-inline">
                <span>Product</span>
                <select
                  value={productId}
                  onChange={(e) => setProductId(Number(e.target.value))}
                  aria-label="Product for order"
                >
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.sku}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field field-inline">
                <span>Qty</span>
                <input
                  type="number"
                  min={1}
                  value={delta}
                  onChange={(e) => setDelta(Number(e.target.value))}
                />
              </label>
              <label className="field field-inline">
                <span>Customer email</span>
                <input
                  type="email"
                  value={customerEmail}
                  onChange={(e) => setCustomerEmail(e.target.value)}
                />
              </label>
              <button
                type="button"
                className="btn btn-primary"
                disabled={orderBusy || productId === "" || delta < 1}
                onClick={() => createOrderForPick()}
              >
                {orderBusy && payOrderId === null
                  ? "Creating…"
                  : payOrderId !== null
                    ? "New order"
                    : "Create order"}
              </button>
            </div>

            <div className="workflow-card">
              <div className="workflow-head">
                <h3>Payment</h3>
                {orderStatus ? (
                  <span className={statusPillClass(orderStatus)}>{orderStatus.replaceAll("_", " ")}</span>
                ) : null}
              </div>
              {payOrderId !== null ? (
                <p className="order-meta">
                  Active order <strong>#{payOrderId}</strong>
                </p>
              ) : (
                <p className="muted">Create or load an order to enable checkout.</p>
              )}
              {recentOrders.length > 0 && (
                <div className="table-wrap recent-orders-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Order</th>
                        <th>Status</th>
                        <th className="num">Order total (ZAR)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {recentOrders.map((o) => (
                        <tr
                          key={o.id}
                          className={payOrderId === o.id ? "recent-order-row--active" : "recent-order-row"}
                          onClick={() => void openExistingOrder(o.id)}
                        >
                          <td>#{o.id}</td>
                          <td>
                            <span className={statusPillClass(o.status)}>{o.status.replaceAll("_", " ")}</span>
                          </td>
                          <td className="num" title="orders.total_amount in Postgres">
                            {o.total_amount}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              <div className="movement-form" style={{ marginTop: "0.75rem" }}>
                <label className="field field-inline">
                  <span>Open existing order</span>
                  <input
                    type="number"
                    min={1}
                    value={lookupOrderId}
                    aria-label="Order ID"
                    onChange={(e) => setLookupOrderId(e.target.value)}
                    placeholder="From table above"
                  />
                </label>
                <button
                  type="button"
                  className="btn btn-ghost"
                  style={{ color: "var(--text)", border: "1px solid var(--border)" }}
                  disabled={orderBusy || lookupOrderId.trim() === ""}
                  onClick={() => void loadOrderFromField()}
                >
                  Load
                </button>
              </div>
              <div className="movement-actions payment-steps">
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={orderBusy}
                  onClick={handleCheckoutClick}
                >
                  {orderBusy ? "Opening…" : "Checkout (Paystack)"}
                </button>
                <button
                  type="button"
                  className="btn btn-success"
                  disabled={orderBusy || payOrderId === null}
                  onClick={() => payOrderId !== null && void confirmPayment(payOrderId)}
                >
                  {orderBusy ? "Working…" : "Confirm payment"}
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  disabled={orderBusy || payOrderId === null}
                  onClick={() => payOrderId !== null && void refreshOrderStatus(payOrderId)}
                >
                  {orderBusy ? "Refreshing…" : "Refresh"}
                </button>
              </div>
              <p className="muted">
                After Paystack Success, click Confirm payment (checks Paystack, then sets status to paid).
              </p>
              {successMessage && <p className="alert alert-success">{successMessage}</p>}
              {error && <p className="alert alert-error">{error}</p>}
            </div>
          </section>

        {orderDetail && (
          <section className="panel panel-subtle">
            <div className="panel-head">
              <h2>Order record</h2>
              <p className="muted">
                Same row as pgAdmin table <code>orders</code> — not <code>order_lines.unit_price</code>
              </p>
            </div>
            <div className="order-record">
              <p className="order-record-title">orders · id {orderDetail.id}</p>
              <dl>
                <dt>Status</dt>
                <dd>
                  <span className={statusPillClass(orderDetail.status)}>
                    {orderDetail.status.replaceAll("_", " ")}
                  </span>
                </dd>
                <dt>Customer</dt>
                <dd>{orderDetail.customer_email}</dd>
                <dt>Total</dt>
                <dd>
                  {orderDetail.currency} {orderDetail.total_amount}
                </dd>
                <dt>Paystack ref</dt>
                <dd>{orderDetail.paystack_reference ?? "—"}</dd>
                {receiptBody && (
                  <>
                    <dt>Receipt</dt>
                    <dd>
                      <pre className="receipt-body">{receiptBody}</pre>
                    </dd>
                  </>
                )}
              </dl>
            </div>
          </section>
        )}
          </div>
        )}

        {role !== "supervisor" && (
        <section className="panel">
          <div className="panel-head">
            <h2>Stock movement</h2>
            <p className="muted">Append a delivery or pick to the ledger</p>
          </div>
          <div className="movement-form">
            <label className="field field-inline">
              <span>Product</span>
              <select
                value={productId}
                onChange={(e) => setProductId(Number(e.target.value))}
                aria-label="Product"
              >
                {products.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.sku}
                  </option>
                ))}
              </select>
            </label>
            <label className="field field-inline">
              <span>Quantity</span>
              <input
                type="number"
                min={1}
                value={delta}
                onChange={(e) => setDelta(Number(e.target.value))}
                aria-label="Quantity"
              />
            </label>
            <div className="movement-actions">
              <button
                type="button"
                className="btn btn-success"
                disabled={!canDeliver || loading || delta < 1}
                onClick={() => recordMovement(1)}
                title={canDeliver ? "Add stock to shelf" : "Receiver role only"}
              >
                Receive stock
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                disabled={!canPick || loading || delta < 1 || activeOrderId === null}
                onClick={() => recordMovement(-1)}
                title={
                  canPick
                    ? activeOrderId
                      ? `Pick for order #${activeOrderId}`
                      : "Create an order first"
                    : "Picker role only"
                }
              >
                Pick / ship
              </button>
            </div>
          </div>
          {successMessage && <p className="alert alert-success">{successMessage}</p>}
          {error && <p className="alert alert-error">{error}</p>}
        </section>
        )}

        <section className="panel">
          <div className="panel-head panel-head-row">
            <div>
              <h2>Activity</h2>
              <p className="muted">
                Recent ledger movements
                {dbInfo ? ` · ${dbInfo.stock_movement_rows} total rows` : ""}
              </p>
            </div>
            <button
              type="button"
              className="btn btn-secondary"
              disabled={!token || loading}
              onClick={() => token && void loadRecentMovements(token)}
            >
              Refresh list
            </button>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Qty Δ</th>
                  <th>Order</th>
                  <th>When</th>
                </tr>
              </thead>
              <tbody>
                {recentLoadProblem ? (
                  <tr>
                    <td colSpan={4} className="alert alert-error">
                      {recentLoadProblem}
                    </td>
                  </tr>
                ) : recentMovements.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="muted">
                      No movements yet.
                    </td>
                  </tr>
                ) : (
                  recentMovements.map((m) => (
                    <tr key={m.id}>
                      <td>#{m.id}</td>
                      <td className={m.quantity_delta > 0 ? "delta-plus" : "delta-minus"}>
                        {m.quantity_delta > 0 ? "+" : ""}
                        {m.quantity_delta}
                      </td>
                      <td>{m.order_id ?? "—"}</td>
                      <td>{new Date(m.created_at).toLocaleString()}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        {dbInfo && (
          <footer className="app-footer">
            Connected to <kbd>{dbInfo.database_name}</kbd> @ {dbInfo.database_host}:{dbInfo.database_port}
          </footer>
        )}
      </main>
    </div>
  );
}