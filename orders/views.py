import datetime
from django.shortcuts import redirect, render
from django.http import HttpResponse, JsonResponse
from carts.models import CartItem
from .forms import OrderForm
from .models import Order, Payment, OrderProduct
import razorpay
from django.views.decorators.csrf import csrf_exempt
from greatkart.settings import RAZORPAY_API_KEY_ID, RAZORPAY_API_KEY_SECRET
import json
# Create your views here.

# 2.setting the credentials of razorpay
client = razorpay.Client(auth=(RAZORPAY_API_KEY_ID, RAZORPAY_API_KEY_SECRET))




def payments(request):
    body = json.loads(request.body)
    order = Order.objects.get(user=request.user, is_ordered=False, order_number=body['orderID'])

    # Store transaction details inside Payment model
    payment = Payment(
        user = request.user,
        payment_id = body['transID'],
        payment_method = body['payment_method'],
        amount_paid = order.order_total,
        status = body['status'],
    )
    payment.save()

    order.payment = payment
    order.is_ordered = True
    order.save()

    return render(request, 'orders/payments.html')




def place_order(request, total=0, quantity=0):
    current_user = request.user
    # If cart item is less than or equal to 0, then redirect them to store page 
    cart_items = CartItem.objects.filter(user=current_user)
    cart_count = cart_items.count()
    if cart_count <= 0:
        return redirect('store')

    grand_total = 0
    tax = 0
    for cart_item in cart_items:
        total += (cart_item.product.price * cart_item.quantity)
        quantity += cart_item.quantity
    tax = (2*total)/100
    grand_total = (total + tax)

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            # store all the billing info inside order table
            data = Order()
            data.user = current_user
            data.first_name = form.cleaned_data['first_name']
            data.last_name = form.cleaned_data['last_name']
            data.phone = form.cleaned_data['phone']
            data.email = form.cleaned_data['email']
            data.address_line_1 = form.cleaned_data['address_line_1']
            data.address_line_2 = form.cleaned_data['address_line_2']
            data.country = form.cleaned_data['country']
            data.state = form.cleaned_data['state']
            data.city = form.cleaned_data['city']
            data.order_note = form.cleaned_data['order_note']
            data.order_total = grand_total
            data.tax = tax
            data.ip = request.META.get('REMOTE_ADDR')
            data.save()

            # Generate order number
            yr = int(datetime.date.today().strftime('%Y'))
            dt = int(datetime.date.today().strftime('%d'))
            mt = int(datetime.date.today().strftime('%m'))
            d = datetime.date(yr,mt,dt)
            current_date = d.strftime("%Y%m%d") #20220126
            order_number = current_date + str(data.id)
            data.order_number = order_number
            data.save()

            order = Order.objects.get(user=current_user, is_ordered=False, order_number=order_number)

            #3. Razorpay Integration
            # (order creation of razorpay)
            DATA = {
                "amount": grand_total*100,
                "currency": "INR",
                "payment_capture": 1,
            }
            payment_order = client.order.create(data=DATA)
            print(payment_order)
            payment_order_id = payment_order['id']


            context = {
            'order': order,
            'cart_items': cart_items,
            'total': total,
            'tax': tax,
            'grand_total': grand_total,
            'api_key_id': RAZORPAY_API_KEY_ID,
            'order_id': payment_order_id,
            }
            
            return render(request, 'orders/payments.html', context)

    else:
        return redirect('checkout')


    
        
def order_complete(request):
    
    return HttpResponse('success')







