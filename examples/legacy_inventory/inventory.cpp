#include "inventory.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>

Inventory::Inventory() : items_(NULL), size_(0) {
    items_ = new Item*[MAX_ITEMS];
    for (int i = 0; i < MAX_ITEMS; i++) {
        items_[i] = NULL;
    }
}

Inventory::~Inventory() {
    for (int i = 0; i < size_; i++) {
        delete items_[i];
    }
    delete[] items_;
}

bool Inventory::add(const char* sku, const char* name, int quantity, double unitPrice) {
    if (sku == NULL || name == NULL || quantity < 0 || unitPrice < 0) {
        return false;
    }
    if (size_ >= MAX_ITEMS || find(sku) != NULL) {
        return false;
    }
    Item* item = new Item;
    item->sku = sku;
    item->name = name;
    item->quantity = quantity;
    item->unitPrice = unitPrice;
    items_[size_++] = item;
    return true;
}

Item* Inventory::find(const std::string& sku) const {
    for (int i = 0; i < size_; i++) {
        if (items_[i]->sku == sku) {
            return items_[i];
        }
    }
    return NULL;
}

bool Inventory::remove(const std::string& sku) {
    for (int i = 0; i < size_; i++) {
        if (items_[i]->sku == sku) {
            delete items_[i];
            for (int j = i; j < size_ - 1; j++) {
                items_[j] = items_[j + 1];
            }
            items_[--size_] = NULL;
            return true;
        }
    }
    return false;
}

int Inventory::count() const {
    return size_;
}

double Inventory::totalValue() const {
    double total = 0;
    for (int i = 0; i < size_; i++) {
        total += (double)items_[i]->quantity * items_[i]->unitPrice;
    }
    return total;
}

NameList Inventory::lowStock() const {
    NameList names;
    for (int i = 0; i < size_; i++) {
        if (items_[i]->quantity < LOW_STOCK_THRESHOLD) {
            names.push_back(items_[i]->name);
        }
    }
    return names;
}

char* Inventory::report() const {
    char* out = (char*)malloc(64 * (size_ + 1));
    out[0] = '\0';
    char line[64];
    for (int i = 0; i < size_; i++) {
        sprintf(line, "%s x%d\n", items_[i]->sku.c_str(), items_[i]->quantity);
        strcat(out, line);
    }
    return out;
}
