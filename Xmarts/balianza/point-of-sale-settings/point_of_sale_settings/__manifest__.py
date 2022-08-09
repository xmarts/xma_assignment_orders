# -*- coding: utf-8 -*-
{
    'name': "Ajustes PDV",
    'summary': """ """,
    'description': """
        Este módulo contiene:
            -Manejo de Cantidades desde PTV\n
            -Agregar un campo check para determinar si es obligatorio o no el escaneo del producto para la selección desde PTV\n
            -Manejo de Cajas y Unidades desde PTV\n
            -Visibilidad de stock actual al seleccionar un producto y Gestión de lotes y caducidades en PTV\n
            -Reserva de producto al momento de añadir cantidades desde PTV\n
            -Creación registro clientes desde PTV\n
            -Funcionalidad búsqueda de clientes por código en PTV\n
            -Validaciones si ya existe RFC registrados y no permitir duplicidad en PTV\n
            -Restricción en selección de lista de precios (Tarifas) debe solo tomar por defecto la que se asigna en el cliente en PTV\n
            -Modificación en interfaz de las lineas de las ordenes para relación de serie desde PDV\n
            -En ventas al crear una orden deberá existir una pestaña de selección para el tipo de venta\n
            -Ventana de seleccion de repartidor y mostrar los datos del repartidor en el ticket desde PDV\n
    """,
    'author': "Xmarts",
    'contributors': "joseluis.vences@xmarts.com",
    'website': "http://www.xmarts.com",
    'category': 'Point of Sale',
    'version': '14.0.1',
    'depends': ['base', 'point_of_sale', 'product', 'mail', 'sale', 'ba_synchronize'],
    'data': [
        'views/inherit_pos_order_views.xml',
        'views/inherit_product_template_views.xml',
        'views/inherit_res_partner_views.xml',
        'views/inherit_sale_orde_views.xml',
        'views/templates.xml',
    ],
    'qweb': [
        'static/src/xml/inherit_client_details_edit.xml',
        'static/src/xml/inherit_numpad_widget.xml',
        'static/src/xml/inherit_order_line.xml',
        'static/src/xml/inherit_order_receipt.xml',
        'static/src/xml/inherit_order_widget.xml',
        'static/src/xml/inherit_payment_screen.xml',
        # 'static/src/xml/inherit_point_of_sale.xml',
        'static/src/xml/inherit_product_item.xml',
        'static/src/xml/inherit_ticket_screen.xml',
        'static/src/xml/modal_dialog.xml',
    ],
}
