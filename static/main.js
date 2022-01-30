$(window).on("load", function(){
    const confirmButtons = $(".action-confirm-delete");
    confirmButtons.on("click", function(){
        $(this).addClass("active");
        $(this).text('Êtes-vous sûr ?');
    })

    const deleteButton = $(".action-delete-product");
    deleteButton.on("click", function(){
        const parent = $(this).closest(".btn-delete-wrapper");
        const form = parent.find(".form-delete-product");
        form.submit();
    })

//Comment

    const abortButton = $(".action-abort-delete");
    abortButton.on("click", function(){
        const parent = $(this).closest(".btn-delete-wrapper");
        const confirmButton = parent.find(".action-confirm-delete");
        confirmButton.removeClass("active");
        setTimeout(function(){
            confirmButton.text('Supprimer ce produit');
        }, 100)

    })

    $('.product-slider').slick({
            infinite: true,
            autoplay: true,
            dots: true,
            slidesToShow: 1,
            slidesToScroll: 1
          });

    $('.accueil-slider').slick({
            infinite: true,
            autoplay: true,
            slidesToShow: 1,
            slidesToScroll: 1,
            autoplaySpeed: 6000
    });
});