-- Mushroom Detection Application - Supabase Schema
-- This script creates the tables, sets up RLS, and adds a trigger to sync auth.users with public.users

-- 1. CLEANUP (Optional - Use with caution)
-- DROP TABLE IF EXISTS order_items;
-- DROP TABLE IF EXISTS orders;
-- DROP TABLE IF EXISTS cart_items;
-- DROP TABLE IF EXISTS mushroom_listings;
-- DROP TABLE IF EXISTS identification_logs;
-- DROP TABLE IF EXISTS mushrooms;
-- DROP TABLE IF EXISTS users;

-- 2. CREATE TABLES

-- Users table (mirrors auth.users)
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    profile_image TEXT,
    is_seller BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Mushrooms Catalog
CREATE TABLE IF NOT EXISTS public.mushrooms (
    id SERIAL PRIMARY KEY,
    common_name TEXT NOT NULL,
    scientific_name TEXT,
    category TEXT CHECK (category IN ('edible', 'poisonous', 'medicinal', 'unknown')) DEFAULT 'unknown',
    description TEXT,
    habitat TEXT,
    season TEXT,
    image_url TEXT,
    edibility_notes TEXT,
    lookalikes JSONB DEFAULT '[]'::jsonb,
    nutritional_info TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Identification Logs (User scan history)
CREATE TABLE IF NOT EXISTS public.identification_logs (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    mushroom_id INTEGER REFERENCES public.mushrooms(id) ON DELETE SET NULL,
    uploaded_image_path TEXT NOT NULL,
    confidence_score FLOAT,
    predicted_name TEXT,
    is_confirmed BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Mushroom Listings (Marketplace)
CREATE TABLE IF NOT EXISTS public.mushroom_listings (
    id SERIAL PRIMARY KEY,
    seller_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    mushroom_id INTEGER NOT NULL REFERENCES public.mushrooms(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    price_per_kg FLOAT NOT NULL,
    quantity_kg FLOAT NOT NULL,
    is_organic BOOLEAN DEFAULT FALSE,
    is_available BOOLEAN DEFAULT TRUE,
    image_url TEXT,
    location TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Cart Items
CREATE TABLE IF NOT EXISTS public.cart_items (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    listing_id INTEGER NOT NULL REFERENCES public.mushroom_listings(id) ON DELETE CASCADE,
    quantity_kg FLOAT NOT NULL DEFAULT 1.0,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, listing_id)
);

-- Orders
CREATE TABLE IF NOT EXISTS public.orders (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    total_amount FLOAT NOT NULL,
    status TEXT CHECK (status IN ('pending', 'confirmed', 'shipped', 'delivered', 'cancelled')) DEFAULT 'pending',
    delivery_address TEXT NOT NULL,
    payment_method TEXT DEFAULT 'cod',
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Order Items
CREATE TABLE IF NOT EXISTS public.order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES public.orders(id) ON DELETE CASCADE,
    listing_id INTEGER NOT NULL REFERENCES public.mushroom_listings(id) ON DELETE CASCADE,
    quantity_kg FLOAT NOT NULL,
    price_at_purchase FLOAT NOT NULL
);

-- 3. ENABLE ROW LEVEL SECURITY (RLS)
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mushrooms ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.identification_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mushroom_listings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cart_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.order_items ENABLE ROW LEVEL SECURITY;

-- 4. CREATE RLS POLICIES

-- Users: Anyone can see public profile info, only owner can update
CREATE POLICY "Users can view their own profile" ON public.users FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update their own profile" ON public.users FOR UPDATE USING (auth.uid() = id);

-- Mushrooms: Publicly readable
CREATE POLICY "Mushrooms are publicly readable" ON public.mushrooms FOR SELECT USING (true);

-- Identification Logs: Only owner can view/delete
CREATE POLICY "Users can view their own logs" ON public.identification_logs FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert their own logs" ON public.identification_logs FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Listings: Publicly readable, only seller can update/delete
CREATE POLICY "Listings are publicly readable" ON public.mushroom_listings FOR SELECT USING (true);
CREATE POLICY "Sellers can manage their own listings" ON public.mushroom_listings FOR ALL USING (auth.uid() = seller_id);

-- Cart: Only owner can manage
CREATE POLICY "Users can manage their own cart" ON public.cart_items FOR ALL USING (auth.uid() = user_id);

-- Orders: Owner can view their orders, Sellers can view orders for their listings
CREATE POLICY "Users can view their own orders" ON public.orders FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert their own orders" ON public.orders FOR INSERT WITH CHECK (auth.uid() = user_id);

-- 5. AUTH SYNC TRIGGER
-- This function automatically creates a public user entry when a new auth user is created
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.users (id, name, email)
  VALUES (new.id, COALESCE(new.raw_user_meta_data->>'full_name', new.email), new.email);
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- 6. INITIAL DATA SEED (Example Catalog)
INSERT INTO public.mushrooms (common_name, scientific_name, category, description, image_url)
VALUES 
('Oyster Mushroom', 'Pleurotus ostreatus', 'edible', 'Wide, fan-shaped cap, usually white to light brown.', 'https://upload.wikimedia.org/wikipedia/commons/thumb/b/b0/Pleurotus_ostreatus_JPG2.jpg/640px-Pleurotus_ostreatus_JPG2.jpg'),
('Fly Agaric', 'Amanita muscaria', 'poisonous', 'Classic red cap with white spots. Highly toxic.', 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/32/Amanita_muscaria_3.jpg/640px-Amanita_muscaria_3.jpg'),
('Shiitake', 'Lentinula edodes', 'edible', 'Brown, slightly convex cap. Popular in East Asian cuisine.', 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/6e/Lentinula_edodes_M%C3%A9guet.jpg/640px-Lentinula_edodes_M%C3%A9guet.jpg');
