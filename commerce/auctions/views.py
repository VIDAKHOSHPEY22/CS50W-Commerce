from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required

from .models import User, Listing, Bid, Comment, Watchlist
from .forms import ListingForm


# صفحه اصلی - نمایش لیست‌های فعال
def index(request):
    listings = Listing.objects.filter(active=True)  # فقط لیست‌های فعال نمایش داده شوند
    return render(request, "auctions/index.html", {"listings": listings})


# نمایش همه لیست‌های فعال
def listing_index(request):
    listings = Listing.objects.filter(active=True)  # فقط لیست‌های فعال نمایش داده شوند
    return render(request, "auctions/listing_index.html", {"listings": listings})


# نمایش جزئیات لیست مزایده
def listing_detail(request, listing_id):
    listing = get_object_or_404(Listing, id=listing_id)
    bids = Bid.objects.filter(listing=listing).order_by('-amount')
    
    highest_bid = bids.first().amount if bids.exists() else listing.starting_bid
    comments = Comment.objects.filter(listing=listing)
    
    in_watchlist = Watchlist.objects.filter(user=request.user, listing=listing).exists() if request.user.is_authenticated else False

    return render(request, "auctions/listing.html", {
        "listing": listing,
        "bids": bids,
        "comments": comments,
        "highest_bid": highest_bid,
        "in_watchlist": in_watchlist
    })


@login_required
def place_bid(request, listing_id):
    listing = get_object_or_404(Listing, id=listing_id)
    bids = Bid.objects.filter(listing=listing).order_by('-amount')
    highest_bid = bids.first().amount if bids.exists() else listing.starting_bid

    if request.method == "POST":
        bid_amount = request.POST.get("bid")  # بررسی مقدار bid قبل از پردازش
        if bid_amount:
            try:
                bid_amount = float(bid_amount)
                if bid_amount > highest_bid:
                    Bid.objects.create(user=request.user, listing=listing, amount=bid_amount)
                    return HttpResponseRedirect(reverse("listing_detail", args=[listing_id]))
                else:
                    return render(request, "auctions/listing.html", {
                        "listing": listing,
                        "bids": bids,
                        "highest_bid": highest_bid,
                        "message": "Your bid must be higher than the current price."
                    })
            except ValueError:
                return render(request, "auctions/listing.html", {
                    "listing": listing,
                    "bids": bids,
                    "highest_bid": highest_bid,
                    "message": "Invalid bid amount."
                })
    
    return HttpResponseRedirect(reverse("listing_detail", args=[listing_id]))
# ثبت نظر (Comment)
@login_required
def add_comment(request, listing_id):
    listing = get_object_or_404(Listing, id=listing_id)

    if request.method == "POST":
        comment_content = request.POST["comment"]
        Comment.objects.create(user=request.user, listing=listing, content=comment_content)
        return HttpResponseRedirect(reverse("listing_detail", args=[listing_id]))


# مدیریت لیست علاقه‌مندی‌ها (Watchlist)
@login_required
def toggle_watchlist(request, listing_id):
    listing = get_object_or_404(Listing, id=listing_id)
    watchlist_item, created = Watchlist.objects.get_or_create(user=request.user, listing=listing)

    if not created:
        watchlist_item.delete()  # اگر قبلاً اضافه شده بود، حذف کن

    return HttpResponseRedirect(reverse("listing_detail", args=[listing_id]))


# نمایش لیست علاقه‌مندی‌های کاربر
@login_required
def watchlist(request):
    watchlist_items = Watchlist.objects.filter(user=request.user)
    return render(request, "auctions/watchlist.html", {"watchlist_items": watchlist_items})


# بستن مزایده و تعیین برنده
@login_required
def close_auction(request, listing_id):
    listing = get_object_or_404(Listing, id=listing_id)

    if request.user == listing.owner:
        bids = Bid.objects.filter(listing=listing).order_by('-amount')

        if bids.exists():
            highest_bid = bids.first()
            listing.active = False
            listing.save()
            message = f"Auction closed! Winner: {highest_bid.user.username} with bid {highest_bid.amount} USD."
        else:
            listing.active = False
            listing.save()
            message = "Auction closed! No bids were placed."

        return render(request, "auctions/listing.html", {
            "listing": listing,
            "message": message,
            "highest_bid": highest_bid.amount if bids.exists() else listing.starting_bid
        })

    return redirect("listing_detail", listing_id=listing_id)


# ایجاد لیست مزایده جدید
@login_required
def create_listing(request):
    if request.method == "POST":
        form = ListingForm(request.POST)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.owner = request.user
            listing.save()
            return HttpResponseRedirect(reverse("index"))
    else:
        form = ListingForm()

    return render(request, "auctions/create_listing.html", {"form": form})


# ورود کاربران
def login_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "auctions/login.html", {"message": "Invalid username and/or password."})
    else:
        return render(request, "auctions/login.html")


# خروج کاربران
def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


# ثبت‌نام کاربران
def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]

        if password != confirmation:
            return render(request, "auctions/register.html", {"message": "Passwords must match."})

        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "auctions/register.html", {"message": "Username already taken."})

        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "auctions/register.html")


# صفحه ماشین‌حساب
def calculator(request):
    return render(request, "auctions/calculator.html")


def about(request):
    return render(request, "auctions/about.html")

def contact(request):
    return render(request, "auctions/contact.html")


def category_listings(request, category):
    listings = Listing.objects.filter(category=category, active=True)
    return render(request, "auctions/index.html", {"listings": listings, "selected_category": category})

@login_required
def my_listings(request):
    listings = Listing.objects.filter(owner=request.user)
    return render(request, "auctions/my_listings.html", {"listings": listings})