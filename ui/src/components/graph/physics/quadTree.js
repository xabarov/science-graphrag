import { fastInvSqrt, fastSqrt, getRepulsionMultiplier } from "./forceUtils.js";

/** Barnes–Hut quadtree for O(n log n) repulsion (ported from osint-gr). */
export class QuadTree {
  constructor(boundary, capacity = 4) {
    this.boundary = boundary;
    this.capacity = capacity;
    this.nodes = [];
    this.divided = false;
    this.northeast = null;
    this.northwest = null;
    this.southeast = null;
    this.southwest = null;
    this.centerOfMass = { x: 0, y: 0, mass: 0 };
  }

  insert(node) {
    if (!this.contains(node.x, node.y)) return false;

    if (this.nodes.length < this.capacity && !this.divided) {
      this.nodes.push(node);
      const totalMass = this.centerOfMass.mass + 1;
      this.centerOfMass.x = (this.centerOfMass.x * this.centerOfMass.mass + node.x) / totalMass;
      this.centerOfMass.y = (this.centerOfMass.y * this.centerOfMass.mass + node.y) / totalMass;
      this.centerOfMass.mass = totalMass;
      return true;
    }

    if (!this.divided) {
      this.subdivide();
      const oldNodes = [...this.nodes];
      this.nodes = [];
      this.centerOfMass = { x: 0, y: 0, mass: 0 };

      const midX = this.boundary.x + this.boundary.width / 2;
      const midY = this.boundary.y + this.boundary.height / 2;

      oldNodes.forEach((n) => {
        const quadrant = this.getQuadrantForPoint(n.x, n.y, midX, midY);
        let inserted = false;
        switch (quadrant) {
          case "northeast":
            inserted = this.northeast.insert(n);
            break;
          case "northwest":
            inserted = this.northwest.insert(n);
            break;
          case "southeast":
            inserted = this.southeast.insert(n);
            break;
          case "southwest":
            inserted = this.southwest.insert(n);
            break;
          default:
            break;
        }
        if (!inserted) {
          inserted =
            this.northeast.insert(n) ||
            this.northwest.insert(n) ||
            this.southeast.insert(n) ||
            this.southwest.insert(n);
        }
        if (!inserted) {
          this.nodes.push(n);
        }
      });
      this.updateCenterOfMassFromChildren();
    }

    const midX = this.boundary.x + this.boundary.width / 2;
    const midY = this.boundary.y + this.boundary.height / 2;
    const quadrant = this.getQuadrantForPoint(node.x, node.y, midX, midY);

    let inserted = false;
    switch (quadrant) {
      case "northeast":
        inserted = this.northeast.insert(node);
        break;
      case "northwest":
        inserted = this.northwest.insert(node);
        break;
      case "southeast":
        inserted = this.southeast.insert(node);
        break;
      case "southwest":
        inserted = this.southwest.insert(node);
        break;
      default:
        break;
    }

    if (inserted) {
      this.updateCenterOfMassFromChildren();
      return true;
    }

    if (
      this.northeast.insert(node) ||
      this.northwest.insert(node) ||
      this.southeast.insert(node) ||
      this.southwest.insert(node)
    ) {
      this.updateCenterOfMassFromChildren();
      return true;
    }

    return false;
  }

  updateCenterOfMassFromChildren() {
    if (!this.divided) return;

    let totalMass = 0;
    let totalX = 0;
    let totalY = 0;

    const children = [this.northeast, this.northwest, this.southeast, this.southwest];
    children.forEach((child) => {
      if (child && child.centerOfMass.mass > 0) {
        totalMass += child.centerOfMass.mass;
        totalX += child.centerOfMass.x * child.centerOfMass.mass;
        totalY += child.centerOfMass.y * child.centerOfMass.mass;
      }
    });

    totalMass += this.nodes.length;
    this.nodes.forEach((n) => {
      totalX += n.x;
      totalY += n.y;
    });

    if (totalMass > 0) {
      this.centerOfMass.x = totalX / totalMass;
      this.centerOfMass.y = totalY / totalMass;
      this.centerOfMass.mass = totalMass;
    } else {
      this.centerOfMass = { x: 0, y: 0, mass: 0 };
    }
  }

  subdivide() {
    const x = this.boundary.x;
    const y = this.boundary.y;
    const w = this.boundary.width / 2;
    const h = this.boundary.height / 2;

    this.northeast = new QuadTree({ x: x + w, y, width: w, height: h }, this.capacity);
    this.northwest = new QuadTree({ x, y, width: w, height: h }, this.capacity);
    this.southeast = new QuadTree({ x: x + w, y: y + h, width: w, height: h }, this.capacity);
    this.southwest = new QuadTree({ x, y: y + h, width: w, height: h }, this.capacity);
    this.divided = true;
  }

  contains(px, py) {
    return (
      px >= this.boundary.x &&
      px <= this.boundary.x + this.boundary.width &&
      py >= this.boundary.y &&
      py <= this.boundary.y + this.boundary.height
    );
  }

  getQuadrantForPoint(x, y, midX, midY) {
    if (x >= midX && y >= midY) return "southeast";
    if (x >= midX && y < midY) return "northeast";
    if (x < midX && y >= midY) return "southwest";
    return "northwest";
  }

  calculateRepulsion(nodeX, nodeY, nodeId, nodeType, nodePersonId, nodeTypeMap, repulsionStrength, draggedPos, theta = 0.5) {
    let fx = 0;
    let fy = 0;

    if (!this.divided && this.nodes.length > 0) {
      this.nodes.forEach((other) => {
        if (other.id === nodeId) return;
        if (draggedPos && draggedPos.id === other.id) return;

        const dx = nodeX - other.x;
        const dy = nodeY - other.y;
        const distSq = dx * dx + dy * dy + 1;
        const invDist = fastInvSqrt(distSq);

        const otherType = nodeTypeMap.get(other.id);
        const repulsionMultiplier = getRepulsionMultiplier(nodeType, otherType, nodePersonId, other.personId);
        const forceScale = repulsionStrength > 20000 ? 1.5 : 1.0;
        const force = repulsionStrength * repulsionMultiplier * forceScale * invDist * invDist;
        fx += dx * invDist * force;
        fy += dy * invDist * force;
      });
    } else if (this.divided && this.centerOfMass.mass > 0) {
      const dx = nodeX - this.centerOfMass.x;
      const dy = nodeY - this.centerOfMass.y;
      const distSq = dx * dx + dy * dy + 1;
      const dist = fastSqrt(distSq);
      const s = this.boundary.width;
      const ratio = s / dist;

      if (ratio < theta) {
        const invDist = fastInvSqrt(distSq);
        const forceScale = repulsionStrength > 20000 ? 1.5 : 1.0;
        const force = repulsionStrength * this.centerOfMass.mass * forceScale * invDist * invDist;
        fx += dx * invDist * force;
        fy += dy * invDist * force;
      } else {
        const ne = this.northeast.calculateRepulsion(
          nodeX,
          nodeY,
          nodeId,
          nodeType,
          nodePersonId,
          nodeTypeMap,
          repulsionStrength,
          draggedPos,
          theta,
        );
        const nw = this.northwest.calculateRepulsion(
          nodeX,
          nodeY,
          nodeId,
          nodeType,
          nodePersonId,
          nodeTypeMap,
          repulsionStrength,
          draggedPos,
          theta,
        );
        const se = this.southeast.calculateRepulsion(
          nodeX,
          nodeY,
          nodeId,
          nodeType,
          nodePersonId,
          nodeTypeMap,
          repulsionStrength,
          draggedPos,
          theta,
        );
        const sw = this.southwest.calculateRepulsion(
          nodeX,
          nodeY,
          nodeId,
          nodeType,
          nodePersonId,
          nodeTypeMap,
          repulsionStrength,
          draggedPos,
          theta,
        );
        fx += ne.fx + nw.fx + se.fx + sw.fx;
        fy += ne.fy + nw.fy + se.fy + sw.fy;
      }
    }

    return { fx, fy };
  }
}
