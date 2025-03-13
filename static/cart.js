document.addEventListener("DOMContentLoaded", function () {
    let cartCountElement = document.querySelector("#cartCount");
    let cartBody = document.querySelector("#cart-body");
    let cartTotalElement = document.querySelector("#cart-total");

    let cart = JSON.parse(localStorage.getItem("cart")) || [];

    // Update Cart UI
    function updateCartUI() {
        cartBody.innerHTML = "";
        let totalPrice = 0;
        cart.forEach((item, index) => {
            let row = document.createElement("tr");
            row.innerHTML = `
                <td>${item.name}</td>
                <td>$${item.price.toFixed(2)}</td>
                <td>${item.quantity}</td>
                <td>$${(item.price * item.quantity).toFixed(2)}</td>
                <td>
                    <button class="btn btn-danger btn-sm" onclick="removeFromCart(${index})">Remove</button>
                </td>
            `;
            cartBody.appendChild(row);
            totalPrice += item.price * item.quantity;
        });

        cartTotalElement.innerText = totalPrice.toFixed(2);
        cartCountElement.innerText = cart.length;
        localStorage.setItem("cart", JSON.stringify(cart));
    }

    // Add Item to Cart
    window.addToCart = function (name, price) {
        let existingItem = cart.find(item => item.name === name);
        if (existingItem) {
            existingItem.quantity += 1;
        } else {
            cart.push({ name, price, quantity: 1 });
        }
        updateCartUI();
        alert("Item added to cart");
    };

    // Remove Item from Cart
    window.removeFromCart = function (index) {
        cart.splice(index, 1);
        updateCartUI();
    };

    // Clear Cart
    window.clearCart = function () {
        cart = [];
        updateCartUI();
        alert("Cart cleared!");
    };

    // Initialize UI
    updateCartUI();
});
