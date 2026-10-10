/* =========================================================
   MediKart - Cart JavaScript
   ========================================================= */


/* =========================
   ADD ITEM TO CART
   ========================= */

async function addCart(event, medicineId) {
    event.preventDefault();

    const qtyInput = document.getElementById("qty");

    let quantity = 1;

    if (qtyInput) {
        quantity = parseInt(qtyInput.value, 10);

        if (isNaN(quantity) || quantity < 1) {
            alert("Please enter a valid quantity.");
            return;
        }
    }

    try {
        const response = await fetch("/api/cart/add", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                medicine_id: medicineId,
                quantity: quantity
            })
        });

        if (!response.ok) {
            throw new Error("Server error: " + response.status);
        }

        const data = await response.json();

        if (data.success) {
            alert(data.message || "Medicine added to cart.");
            window.location.href = "/cart";
        } else {
            alert(data.message || "Unable to add medicine to cart.");
        }

    } catch (error) {
        console.error("Add cart error:", error);
        alert("Something went wrong. Please try again.");
    }
}


/* =========================
   UPDATE CART ITEM
   ========================= */

async function updateCart(itemId, quantity) {

    quantity = parseInt(quantity, 10);

    if (isNaN(quantity) || quantity < 1) {
        alert("Quantity must be at least 1.");
        window.location.reload();
        return;
    }

    try {
        const formData = new FormData();

        formData.append("item_id", itemId);
        formData.append("quantity", quantity);

        const response = await fetch("/api/cart/update", {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            throw new Error("Server error: " + response.status);
        }

        const data = await response.json();

        if (!data.success) {
            alert(data.message || "Unable to update cart.");
            return;
        }

        window.location.reload();

    } catch (error) {
        console.error("Update cart error:", error);
        alert("Something went wrong while updating the cart.");
    }
}


/* =========================
   REMOVE ITEM FROM CART
   ========================= */

async function removeCart(itemId) {

    const confirmRemove = confirm(
        "Are you sure you want to remove this medicine from your cart?"
    );

    if (!confirmRemove) {
        return;
    }

    try {
        const formData = new FormData();

        formData.append("item_id", itemId);

        const response = await fetch("/api/cart/remove", {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            throw new Error("Server error: " + response.status);
        }

        const data = await response.json();

        if (!data.success) {
            alert(data.message || "Unable to remove item.");
            return;
        }

        window.location.reload();

    } catch (error) {
        console.error("Remove cart error:", error);
        alert("Something went wrong while removing the item.");
    }
}